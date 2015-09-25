import os
import os.path
import types
import string
import logging
import datetime
import threading
from sqlalchemy import (
    create_engine,
    and_,
    Column, Boolean, Integer, DateTime, ForeignKey,
    String, Text, UnicodeText)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    scoped_session, sessionmaker,
    relationship, backref, load_only, subqueryload, joinedload,
    Load)
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import Session
from wikked.db.base import Database, PageListNotFound
from wikked.page import Page, PageData, FileSystemPage
from wikked.utils import split_page_url


logger = logging.getLogger(__name__)


Base = declarative_base()


class SQLPage(Base):
    __tablename__ = 'pages'

    id = Column(Integer, primary_key=True)
    cache_time = Column(DateTime)
    # In the spirit of cross-platformness we let Windows' suckiness dictacte
    # this length (but it's good because it makes those 2 columns short enough
    # to be indexable by SQL).
    url = Column(String(260), unique=True)
    path = Column(String(260), unique=True)
    endpoint = Column(String(64))
    title = Column(UnicodeText)
    raw_text = Column(UnicodeText(length=2 ** 31))
    formatted_text = Column(UnicodeText(length=2 ** 31))

    meta = relationship(
        'SQLMeta',
        order_by='SQLMeta.id',
        backref=backref('page'),
        cascade='all, delete, delete-orphan')
    links = relationship(
        'SQLLink',
        order_by='SQLLink.id',
        backref=backref('source'),
        cascade='all, delete, delete-orphan')

    ready_text = Column(UnicodeText(length=2 ** 31))
    is_ready = Column(Boolean)
    needs_invalidate = Column(Boolean)

    ready_meta = relationship(
        'SQLReadyMeta',
        order_by='SQLReadyMeta.id',
        backref=backref('page'),
        cascade='all, delete, delete-orphan')
    ready_links = relationship(
        'SQLReadyLink',
        order_by='SQLReadyLink.id',
        backref=backref('source'),
        cascade='all, delete, delete-orphan')


class SQLMeta(Base):
    __tablename__ = 'meta'

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('pages.id'))
    name = Column(String(128), index=True)
    value = Column(Text)

    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value


class SQLReadyMeta(Base):
    __tablename__ = 'ready_meta'

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('pages.id'))
    name = Column(String(128), index=True)
    value = Column(Text)

    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value


class SQLLink(Base):
    __tablename__ = 'links'

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('pages.id'))
    target_url = Column(Text)

    def __init__(self, target_url=None):
        self.target_url = target_url


class SQLReadyLink(Base):
    __tablename__ = 'ready_links'

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('pages.id'))
    target_url = Column(Text)

    def __init__(self, target_url=None):
        self.target_url = target_url


class SQLInfo(Base):
    __tablename__ = 'info'

    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    str_value = Column(String(256))
    int_value = Column(Integer)
    time_value = Column(DateTime)


class SQLPageList(Base):
    __tablename__ = 'page_lists'

    id = Column(Integer, primary_key=True)
    list_name = Column(String(64), unique=True)
    is_valid = Column(Boolean)

    page_refs = relationship(
        'SQLPageListItem',
        order_by='SQLPageListItem.id',
        cascade='all, delete, delete-orphan')


class SQLPageListItem(Base):
    __tablename__ = 'page_list_items'

    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey('page_lists.id'))
    page_id = Column(Integer, ForeignKey('pages.id'))

    page = relationship(
            'SQLPage')


class _WikkedSQLSession(Session):
    """ A session that can get its engine to bind to from a state
        object. This effectively makes it possible to setup a session
        factory before we have an engine.
    """
    def __init__(self, state, autocommit=False, autoflush=True):
        self.state = state
        super(_WikkedSQLSession, self).__init__(
                autocommit=autocommit,
                autoflush=autoflush,
                bind=state.engine)


class _SQLStateBase(object):
    """ Base class for the 2 different state holder objects used by
        the `SQLDatabase` cache. One is the "default" one, which is used
        by command line wikis. The other is used when running the Flask
        application, and stays active for as long as the application is
        running. This makes it possible to reuse the same engine and
        session factory.
    """
    def __init__(self, engine_url, scopefunc=None, connect_args=None):
        logger.debug("Creating SQL state.")
        self.engine_url = engine_url
        self.connect_args = connect_args or {}
        self._engine = None
        self._engine_lock = threading.Lock()
        self.session = scoped_session(
                self._createScopedSession,
                scopefunc=scopefunc)

    @property
    def engine(self):
        """ Returns the SQL engine. An engine will be created if there
            wasn't one already. """
        if self._engine is None:
            with self._engine_lock:
                if self._engine is None:
                    logger.debug("Creating SQL engine with URL: %s" %
                                 self.engine_url)
                    self._engine = create_engine(
                            self.engine_url,
                            connect_args=self.connect_args,
                            convert_unicode=True)
        return self._engine

    def close(self, exception=None):
        logger.debug("Closing SQL session.")
        self.session.remove()

    def _createScopedSession(self, **kwargs):
        """ The factory for SQL sessions. When a session is created,
            it will pull the engine in, which will lazily create the
            engine. """
        logger.debug("Creating SQL session.")
        return _WikkedSQLSession(self, **kwargs)


class _SharedSQLState(_SQLStateBase):
    """ The shared state, used when running the Flask application.
    """
    def __init__(self, app, engine_url, scopefunc):
        super(_SharedSQLState, self).__init__(engine_url, scopefunc)
        self.app = app

    def postInitHook(self, wiki):
        wiki.db._state = self


class _EmbeddedSQLState(_SQLStateBase):
    """ The embedded state, used by default in command line wikis.
    """
    def __init__(self, engine_url):
        super(_EmbeddedSQLState, self).__init__(
                engine_url, connect_args={'check_same_thread': False})


class SQLDatabase(Database):
    """ A database cache based on SQL.
    """
    schema_version = 8

    def __init__(self, config):
        Database.__init__(self)
        self.engine_url = config.get('wiki', 'database_url')
        self.auto_update = config.getboolean('wiki', 'auto_update')
        self._state = None
        self._state_lock = threading.Lock()

    def hookupWebApp(self, app):
        """ Hook up a Flask application with all the stuff we need.
            This includes patching every wiki created during request
            handling to use our `_SharedSQLState` object, and removing
            any active sessions after the request is done. """
        from flask import g, _app_ctx_stack

        logger.debug("Hooking up Flask app for SQL database.")
        state = _SharedSQLState(app, self.engine_url,
                                _app_ctx_stack.__ident_func__)
        app.wikked_post_init.append(state.postInitHook)

        @app.teardown_appcontext
        def shutdown_session(exception=None):
            # See if the wiki, and its DB, were used...
            wiki = getattr(g, 'wiki', None)
            if wiki and wiki.db._state:
                wiki.db._state.close(
                        exception=exception)
            return exception

    @property
    def engine(self):
        return self._getState().engine

    @property
    def session(self):
        return self._getState().session

    def _getState(self):
        """ If no state has been specified yet, use the default
            embedded one (which means no sharing of engines or session
            factories with any other wiki instances).
        """
        if self._state is not None:
            return self._state
        with self._state_lock:
            if self._state is None:
                self._state = _EmbeddedSQLState(self.engine_url)
        return self._state

    def _needsSchemaUpdate(self):
        if (self.engine_url == 'sqlite://' or
                self.engine_url == 'sqlite:///:memory:'):
            # Always create the schema for a memory database.
            return True

        # The existing schema is outdated, re-create it.
        schema_version = self._getSchemaVersion()
        if schema_version < self.schema_version:
            logger.debug(
                "SQL database is outdated (got version %s), "
                "will re-create.",
                schema_version)
            return True
        else:
            logger.debug(
                "SQL database has up-to-date schema.")
            return False

    def _createSchema(self):
        logger.debug("Creating new SQL schema.")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

        ver = SQLInfo()
        ver.name = 'schema_version'
        ver.int_value = self.schema_version
        self.session.add(ver)
        self.session.commit()

    def _getSchemaVersion(self):
        try:
            q = self.session.query(SQLInfo).\
                    filter(SQLInfo.name == 'schema_version').\
                    first()
            if q is None:
                return 0
        except:
            return -1
        return q.int_value

    def init(self, wiki):
        pass

    def postInit(self):
        logger.info("Initializing SQL database.")
        self._createSchema()

    def start(self, wiki):
        self.wiki = wiki

    def close(self, exception):
        if self._state is not None:
            self._state.close(exception)

    def reset(self, page_infos):
        logger.debug("Re-creating SQL database.")
        self._createSchema()
        for pi in page_infos:
            page = FileSystemPage(self.wiki, pi)
            self._addPage(page)
        self.session.commit()

    def updatePage(self, page_info):
        if self._needsSchemaUpdate():
            raise Exception("This wiki needs a database update. "
                            "Please run `wk reset`.")

        logger.debug("Updating SQL database for page: %s" % page_info.url)

        db_page = self.session.query(SQLPage).\
                options(load_only('id', 'url')).\
                filter(SQLPage.url == page_info.url).\
                first()
        if db_page:
            logger.debug("Removing page '%s' [%d] from SQL database." %
                    (db_page.url, db_page.id))
            self.session.delete(db_page)
            self.session.commit()

        page = FileSystemPage(self.wiki, page_info)
        self._addPage(page)
        self.session.commit()

    def updateAll(self, page_infos, force=False):
        if self._needsSchemaUpdate():
            raise Exception("This wiki needs a database upgrade. "
                            "Please run `wk reset`.")

        logger.debug("Updating SQL database...")

        to_update = set()
        already_added = set()
        to_remove = []
        page_infos = list(page_infos)
        page_urls = set([p.url for p in page_infos])
        db_pages = self.session.query(SQLPage).\
            options(load_only('id', 'url', 'path', 'cache_time')).\
            all()
        for p in db_pages:
            if not os.path.isfile(p.path):
                # File was deleted.
                to_remove.append(p)
            else:
                already_added.add(p.path)
                path_time = datetime.datetime.fromtimestamp(
                    os.path.getmtime(p.path))
                if path_time > p.cache_time or (force and p.url in page_urls):
                    # File has changed since last index.
                    to_remove.append(p)
                    to_update.add(p.path)
        for p in to_remove:
            logger.debug("Removing page '%s' [%d] from SQL database." %
                (p.url, p.id))
            self.session.delete(p)

        self.session.commit()

        added_db_objs = []
        for pi in page_infos:
            if (pi.path in to_update or
                    pi.path not in already_added):
                page = FileSystemPage(self.wiki, pi)
                added_db_objs.append(self._addPage(page))

        self.session.commit()

        logger.debug("...done updating SQL database.")
        return [o.id for o in added_db_objs]

    def getPageUrls(self, subdir=None, uncached_only=False):
        q = self.session.query(SQLPage.url, SQLPage.is_ready)
        if subdir:
            subdir = string.rstrip(subdir, '/') + '/%'
            q = q.filter(SQLPage.url.like(subdir))
        if uncached_only:
            q = q.filter(SQLPage.is_ready == False)
        for p in q.all():
            yield p.url

    def getPages(self, subdir=None, meta_query=None, uncached_only=False,
                 endpoint_only=None, no_endpoint_only=False, fields=None):
        q = self.session.query(SQLPage)
        if meta_query:
            q = q.join(SQLReadyMeta)
            for name, values in meta_query.items():
                for v in values:
                    q = q.filter(and_(SQLReadyMeta.name == name,
                        SQLReadyMeta.value == v))
        if subdir:
            subdir = string.rstrip(subdir, '/') + '/%'
            q = q.filter(SQLPage.url.like(subdir))
        if uncached_only:
            q = q.filter(SQLPage.is_ready is False)
        if endpoint_only:
            q = q.filter(SQLPage.endpoint == endpoint_only)
        elif no_endpoint_only:
            q = q.filter(SQLPage.endpoint == None)
        q = self._addFieldOptions(q, fields)
        for p in q.all():
            yield SQLDatabasePage(self, p, fields)

    def cachePage(self, page):
        if not hasattr(page, '_id') or not page._id:
            raise Exception("Given page '%s' has no `_id` attribute set." % page.url)

        logger.debug("Caching extended data for page '%s' [%d]." % (page.url, page._id))

        try:
            db_obj = self.session.query(SQLPage).\
                options(load_only('id', 'url')).\
                options(
                    subqueryload('ready_meta'),
                    subqueryload('ready_links')).\
                filter(SQLPage.id == page._id).\
                one()
        except NoResultFound as nrf:
            logging.exception(nrf)
            logging.error("Can't cache page: %s" % page.url)
            raise

        db_obj.ready_text = page._data.text
        db_obj.needs_invalidate = False

        del db_obj.ready_meta[:]
        for name, value in page._data.ext_meta.items():
            if isinstance(value, bool):
                value = ""
            if isinstance(value, str):
                db_obj.ready_meta.append(SQLReadyMeta(name, value))
            else:
                for v in value:
                    db_obj.ready_meta.append(SQLReadyMeta(name, v))
            if name in ['include', 'query']:
                db_obj.needs_invalidate = True

        del db_obj.ready_links[:]
        for link_url in page._data.ext_links:
            db_obj.ready_links.append(SQLReadyLink(link_url))

        db_obj.is_ready = True

        self.session.commit()

    def uncachePages(self, except_url=None, only_required=False):
        q = self.session.query(SQLPage)\
                .options(load_only('id', 'url', 'needs_invalidate', 'is_ready'))
        if except_url:
            q = q.filter(SQLPage.url != except_url)
        if only_required:
            q = q.filter(SQLPage.needs_invalidate == True)

        for p in q.all():
            p.is_ready = False
        self.session.commit()

    def pageExists(self, url=None, path=None):
        q = self.session.query(SQLPage.id, SQLPage.url).filter_by(url=url)
        res = self.session.query(q.exists())
        return res.scalar()

    def getLinksTo(self, url):
        q = self.session.query(SQLReadyLink).\
                filter(SQLReadyLink.target_url == url).\
                join(SQLReadyLink.source).\
                all()
        for l in q:
            yield l.source.url

    def _getPageByUrl(self, url, fields):
        q = self.session.query(SQLPage).\
            filter(SQLPage.url == url)
        q = self._addFieldOptions(q, fields)
        page = q.first()
        if page is None:
            return None
        return SQLDatabasePage(self, page, fields)

    def _getPageByPath(self, path, fields):
        q = self.session.query(SQLPage).\
            filter(SQLPage.path == path)
        q = self._addFieldOptions(q, fields)
        page = q.first()
        if page is None:
            return None
        return SQLDatabasePage(self, page, fields)

    def _addFieldOptions(self, query, fields, use_joined=True,
            use_load_obj=False):
        if fields is None:
            return query

        if use_load_obj:
            obj = Load(SQLPage)
            l_load_only = obj.load_only
            l_joinedload = obj.joinedload
            l_subqueryload = obj.subqueryload
        else:
            l_load_only = load_only
            l_joinedload = joinedload
            l_subqueryload = subqueryload

        fieldnames = {
                'local_meta': SQLPage.meta,
                'local_links': SQLPage.links,
                'meta': SQLPage.ready_meta,
                'links': SQLPage.ready_links,
                'text': SQLPage.ready_text,
                'is_resolved': SQLPage.is_ready}
        subqueryfields = {
                'local_meta': SQLPage.meta,
                'local_links': SQLPage.links,
                'meta': SQLPage.ready_meta,
                'links': SQLPage.ready_links}
        # Always load the ID.
        query = query.options(l_load_only(SQLPage.id))
        # Load requested fields... some need subqueries.
        for f in fields:
            col = fieldnames.get(f) or f
            query = query.options(l_load_only(col))
            sqf = subqueryfields.get(f)
            if sqf:
                if use_joined:
                    query = query.options(l_joinedload(sqf))
                else:
                    query = query.options(l_subqueryload(sqf))
        return query

    def _addPage(self, page):
        logger.debug("Adding page '%s' to SQL database." % page.url)

        po = SQLPage()
        po.cache_time = datetime.datetime.now()
        po.url = page.url
        po.endpoint, _ = split_page_url(page.url)
        po.path = page.path
        po.title = page.title
        po.raw_text = page.raw_text
        po.formatted_text = page.getFormattedText()
        po.ready_text = None
        po.is_ready = False

        for name, value in page.getLocalMeta().items():
            if isinstance(value, bool):
                value = ""
            if isinstance(value, str):
                po.meta.append(SQLMeta(name, value))
            else:
                for v in value:
                    po.meta.append(SQLMeta(name, v))

        for link_url in page.getLocalLinks():
            po.links.append(SQLLink(link_url))

        self.session.add(po)

        return po

    def addPageList(self, list_name, pages):
        page_list = self.session.query(SQLPageList)\
                .filter(SQLPageList.list_name == list_name)\
                .first()
        if page_list is not None:
            # We may have a previous list marked as non-valid. Let's
            # revive it.
            if page_list.is_valid:
                raise Exception("Page list already exists and is valid: %s" % list_name)
            logger.debug("Reviving page list '%s'." % list_name)
            self.session.query(SQLPageListItem)\
                    .filter(SQLPageListItem.list_id == page_list.id)\
                    .delete()
            page_list.is_valid = True
        else:
            logger.debug("Creating page list '%s'." % list_name)
            page_list = SQLPageList()
            page_list.list_name = list_name
            page_list.is_valid = True
            self.session.add(page_list)

        for p in pages:
            item = SQLPageListItem()
            item.page_id = p._id
            page_list.page_refs.append(item)

        self.session.commit()

    def getPageList(self, list_name, fields=None, valid_only=True):
        page_list = self.session.query(SQLPageList)\
                .filter(SQLPageList.list_name == list_name)\
                .first()
        if page_list is None or (
                valid_only and not page_list.is_valid):
            raise PageListNotFound(list_name)

        q = self.session.query(SQLPageListItem)\
                .filter(SQLPageListItem.list_id == page_list.id)\
                .join(SQLPageListItem.page)
        q = self._addFieldOptions(q, fields, use_load_obj=True)
        for po in q.all():
            yield SQLDatabasePage(self, po.page, fields)

    def removePageList(self, list_name):
        # Just mark the list as not valid anymore.
        page_list = self.session.query(SQLPageList)\
                .filter(SQLPageList.list_name == list_name)\
                .first()
        if page_list is None:
            raise Exception("No such list: %s" % list_name)
        page_list.is_valid = False
        self.session.commit()

    def removeAllPageLists(self):
        q = self.session.query(SQLPageList)
        for pl in q.all():
            pl.is_valid = False
        self.session.commit()


class SQLDatabasePage(Page):
    """ A page that can load its properties from a database.
    """
    def __init__(self, db, db_obj, fields):
        data = self._loadFromDbObject(db_obj, fields)
        super(SQLDatabasePage, self).__init__(db.wiki, data)

    @property
    def _id(self):
        return self._data._db_id

    def _loadFromDbObject(self, db_obj, fields):
        data = PageData()
        data._db_id = db_obj.id
        if fields is None or 'url' in fields:
            data.url = db_obj.url
        if fields is None or 'path' in fields:
            data.path = db_obj.path
        if fields is None or 'cache_time' in fields:
            data.cache_time = db_obj.cache_time
        if fields is None or 'is_resolved' in fields:
            data.is_resolved = db_obj.is_ready
        if fields is None or 'title' in fields:
            data.title = db_obj.title
        if fields is None or 'raw_text' in fields:
            data.raw_text = db_obj.raw_text
        if fields is None or 'formatted_text' in fields:
            data.formatted_text = db_obj.formatted_text

        if fields is None or 'local_meta' in fields:
            data.local_meta = {}
            for m in db_obj.meta:
                existing = data.local_meta.get(m.name)
                value = m.value
                if value == '':
                    value = True
                if existing is None:
                    data.local_meta[m.name] = [value]
                else:
                    existing.append(value)

        if fields is None or 'local_links' in fields:
            data.local_links = [l.target_url for l in db_obj.links]

        if fields is None or ('meta' in fields or 'links' in fields or
                              'text' in fields):
            if fields is None or 'text' in fields:
                data.text = db_obj.ready_text

            if fields is None or 'meta' in fields:
                data.ext_meta = {}
                for m in db_obj.ready_meta:
                    existing = data.ext_meta.get(m.name)
                    value = m.value
                    if value == '':
                        value = True
                    if existing is None:
                        data.ext_meta[m.name] = [value]
                    else:
                        existing.append(value)

            if fields is None or 'links' in fields:
                data.ext_links = [l.target_url for l in db_obj.ready_links]

        return data

