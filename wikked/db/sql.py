import os
import os.path
import types
import string
import logging
import datetime
from sqlalchemy import (
    create_engine,
    and_, or_,
    Column, Boolean, Integer, DateTime, ForeignKey,
    String, Text, UnicodeText)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    scoped_session, sessionmaker,
    relationship, backref, load_only, subqueryload)
from sqlalchemy.orm.exc import NoResultFound
from wikked.db.base import Database
from wikked.page import Page, PageData


logger = logging.getLogger(__name__)


Base = declarative_base()


class SQLPage(Base):
    __tablename__ = 'pages'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    # Most browsers/search engines won't accept URLs longer than ~2000 chars.
    url = Column(String(2048))
    # In the spirit of cross-platformness we let Windows' suckiness dictacte
    # this length.
    path = Column(String(260))
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


class SQLDatabase(Database):
    """ A database cache based on SQL.
    """
    schema_version = 3

    def __init__(self, config):
        Database.__init__(self)
        self.engine_url = config.get('wiki', 'database_url')
        self.auto_update = config.getboolean('wiki', 'auto_update')
        self._engine = None
        self._session = None

    @property
    def engine(self):
        if self._engine is None:
            logger.debug("Creating SQL engine from URL: %s" % self.engine_url)
            self._engine = create_engine(self.engine_url, convert_unicode=True)
        return self._engine

    @property
    def session(self):
        if self._session is None:
            logger.debug("Opening database from URL: %s" % self.engine_url)
            self._session = scoped_session(sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine))
        return self._session

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

    def close(self, commit, exception):
        if self._session is not None:
            if commit and exception is None:
                self._session.commit()
            self._session.remove()

    def reset(self, page_infos, page_factory):
        logger.debug("Re-creating SQL database.")
        self._createSchema()
        for pi in page_infos:
            page = page_factory(pi)
            self._addPage(page)
        self.session.commit()

    def update(self, page_infos, page_factory, force=False):
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
            options(load_only('id', 'url', 'path', 'time')).\
            all()
        for p in db_pages:
            if not os.path.isfile(p.path):
                # File was deleted.
                to_remove.append(p)
            else:
                already_added.add(p.path)
                path_time = datetime.datetime.fromtimestamp(
                    os.path.getmtime(p.path))
                if path_time > p.time or (force and p.url in page_urls):
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
                page = page_factory(pi)
                added_db_objs.append(self._addPage(page))

        self.session.commit()

        if to_remove or added_db_objs:
            # If pages have been added/removed/updated, invalidate everything
            # in the wiki that has includes or queries.
            db_pages = self.session.query(SQLPage.id, SQLPage.is_ready,
                                          SQLPage.ready_meta).\
                join(SQLReadyMeta).\
                filter(or_(
                    SQLReadyMeta.name == 'include',
                    SQLReadyMeta.name == 'query')).\
                all()
            for p in db_pages:
                p.is_ready = False

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
                 fields=None):
        q = self.session.query(SQLPage)
        if meta_query:
            q = q.join(SQLReadyMeta)
            for name, values in meta_query.iteritems():
                for v in values:
                    q = q.filter(and_(SQLReadyMeta.name == name,
                        SQLReadyMeta.value == v))
        if subdir:
            subdir = string.rstrip(subdir, '/') + '/%'
            q = q.filter(SQLPage.url.like(subdir))
        if uncached_only:
            q = q.filter(SQLPage.is_ready is False)
        q = self._addFieldOptions(q, fields)
        for p in q.all():
            yield SQLDatabasePage(self, p, fields)

    def isCacheValid(self, page):
        db_obj = self.session.query(SQLPage).\
            options(load_only('id', 'path', 'time')).\
            filter(SQLPage.id == page._id).\
            one()
        path_time = datetime.datetime.fromtimestamp(
            os.path.getmtime(db_obj.path))
        return path_time < db_obj.time

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

        del db_obj.ready_meta[:]
        for name, value in page._data.ext_meta.iteritems():
            if isinstance(value, bool):
                value = ""
            if isinstance(value, types.StringTypes):
                db_obj.ready_meta.append(SQLReadyMeta(name, value))
            else:
                for v in value:
                    db_obj.ready_meta.append(SQLReadyMeta(name, v))

        del db_obj.ready_links[:]
        for link_url in page._data.ext_links:
            db_obj.ready_links.append(SQLReadyLink(link_url))

        db_obj.is_ready = True

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

    def _addFieldOptions(self, query, fields):
        if fields is None:
            return query

        fieldnames = {
                'local_meta': 'meta',
                'local_links': 'links',
                'meta': 'ready_meta',
                'links': 'ready_links'}
        subqueryfields = {
                'local_meta': SQLPage.meta,
                'local_links': SQLPage.links,
                'meta': SQLPage.ready_meta,
                'links': SQLPage.ready_links}
        # Always load the ID.
        query = query.options(load_only('id'))
        # Load requested fields... some need subqueries.
        for f in fields:
            col = fieldnames.get(f) or f
            query = query.options(load_only(col))
            sqf = subqueryfields.get(f)
            if sqf:
                query = query.options(subqueryload(sqf))
        return query

    def _addPage(self, page):
        logger.debug("Adding page '%s' to SQL database." % page.url)

        po = SQLPage()
        po.time = datetime.datetime.now()
        po.url = page.url
        po.path = page.path
        po.title = page.title
        po.raw_text = page.raw_text
        po.formatted_text = page.getFormattedText()
        po.ready_text = None
        po.is_ready = False

        for name, value in page.getLocalMeta().iteritems():
            if isinstance(value, bool):
                value = ""
            if isinstance(value, types.StringTypes):
                po.meta.append(SQLMeta(name, value))
            else:
                for v in value:
                    po.meta.append(SQLMeta(name, v))

        for link_url in page.getLocalLinks():
            po.links.append(SQLLink(link_url))

        self.session.add(po)

        return po


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
            if not db_obj.is_ready:
                raise Exception(
                    "Requested extended data for page '%s' "
                    "but data is not cached in the SQL database." % (
                        data.url or data._db_id))

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
