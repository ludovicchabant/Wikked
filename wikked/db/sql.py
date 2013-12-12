import os
import os.path
import types
import string
import logging
import datetime
from sqlalchemy import (
        create_engine,
        and_, or_,
        Column, Boolean, Integer, String, Text, DateTime, ForeignKey)
from sqlalchemy.orm import (
        scoped_session, sessionmaker,
        relationship, backref, defer)
from sqlalchemy.ext.declarative import declarative_base
from base import Database
from wikked.page import Page, FileSystemPage, PageData, PageLoadingError
from wikked.formatter import SINGLE_METAS
from wikked.utils import PageNotFoundError


logger = logging.getLogger(__name__)


Base = declarative_base()


class SQLPage(Base):
    __tablename__ = 'pages'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    url = Column(Text)
    path = Column(Text)
    title = Column(Text)
    raw_text = Column(Text)
    formatted_text = Column(Text)
    
    meta = relationship('SQLMeta', order_by='SQLMeta.id', 
            backref=backref('page'),
            cascade='all, delete, delete-orphan')
    links = relationship('SQLLink', order_by='SQLLink.id', 
            backref=backref('source'),
            cascade='all, delete, delete-orphan')

    ready_text = Column(Text)
    is_ready = Column(Boolean)

    ready_meta = relationship('SQLReadyMeta', order_by='SQLReadyMeta.id',
            backref=backref('page'),
            cascade='all, delete, delete-orphan')
    ready_links = relationship('SQLReadyLink', order_by='SQLReadyLink.id', 
            backref=backref('source'),
            cascade='all, delete, delete-orphan')


class SQLMeta(Base):
    __tablename__ = 'meta'

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('pages.id'))
    name = Column(String(128))
    value = Column(Text)

    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value


class SQLReadyMeta(Base):
    __tablename__ = 'ready_meta'

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('pages.id'))
    name = Column(String(128))
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

    def __init__(self):
        Database.__init__(self)
        self.engine = None

    def initDb(self, wiki):
        self.wiki = wiki

        engine_url = wiki.config.get('wiki', 'database_url')
        logger.info("Using database from URL: %s" % engine_url)
        self.engine = create_engine(engine_url, convert_unicode=True)
        self.session = scoped_session(sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine))

        Base.query = self.session.query_property()

        create_schema = False
        if engine_url != 'sqlite:///:memory:':
            # The existing schema is outdated, re-create it.
            schema_version = self._getSchemaVersion()
            if schema_version < self.schema_version:
                logger.debug(
                        "SQL database is outdated (got version %s), will re-create.",
                        schema_version)
                create_schema = True
            else:
                logger.debug(
                        "SQL database has up-to-date schema.")
        else:
            create_schema = True
        if create_schema:
            self._createSchema()

    def open(self):
        logger.debug("Opening connection")

    def close(self):
        logger.debug("Closing connection")

    def reset(self, pages):
        logger.debug("Re-creating SQL database.")
        self._createSchema()
        for page in pages:
            self._addPage(page)
        self.session.commit()

    def update(self, pages, force=False):
        to_update = set()
        already_added = set()
        to_remove = []
        pages = list(pages)

        logger.debug("Updating SQL database...")
        page_urls = [p.url for p in pages]
        db_pages = self.session.query(SQLPage).\
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
            self._removePage(p)

        self.session.commit()

        added_db_objs = []
        for p in pages:
            if (p.path in to_update or
                p.path not in already_added):
                added_db_objs.append(self._addPage(p))

        self.session.commit()

        if to_remove or added_db_objs:
            # If pages have been added/removed/updated, invalidate everything
            # in the wiki that has includes or queries.
            db_pages = self.session.query(SQLPage).\
                    options(
                            defer(SQLPage.title),
                            defer(SQLPage.raw_text),
                            defer(SQLPage.formatted_text),
                            defer(SQLPage.ready_text)).\
                    join(SQLReadyMeta).\
                    filter(or_(SQLReadyMeta.name == 'include', SQLReadyMeta.name == 'query')).\
                    all()
            for p in db_pages:
                p.is_ready = False
            
            self.session.commit()

        logger.debug("...done updating SQL database.")
        return [o.id for o in added_db_objs]

    def getPageUrls(self, subdir=None):
        q = self.session.query(SQLPage.url)
        if subdir:
            subdir = string.rstrip(subdir, '/') + '/%'
            q = q.filter(SQLPage.url.like(subdir))
        urls = []
        for p in q.all():
            urls.append(p.url)
        return urls

    def getPages(self, subdir=None, meta_query=None):
        q = self.session.query(SQLPage)
        if meta_query:
            q = q.join(SQLReadyMeta)
            for name, values in meta_query.iteritems():
                for v in values:
                    q = q.filter(and_(SQLReadyMeta.name == name, SQLReadyMeta.value == v))
        if subdir:
            subdir = string.rstrip(subdir, '/') + '/%'
            q = q.filter(SQLPage.url.like(subdir))
        for p in q.all():
            yield SQLDatabasePage(self.wiki, db_obj=p)

    def pageExists(self, url=None, path=None):
        # TODO: replace with an `EXIST` query.
        return self.getPage(url, path, raise_if_none=False) is not None

    def getLinksTo(self, url):
        q = self.session.query(SQLReadyLink).\
                filter(SQLReadyLink.target_url == url).\
                join(SQLReadyLink.source).\
                all()
        for l in q:
            yield l.source.url

    def getUncachedPages(self):
        q = self.session.query(SQLPage).\
                filter(SQLPage.is_ready == False).\
                all()
        for p in q:
            yield SQLDatabasePage(self.wiki, db_obj=p)

    def _getPageByUrl(self, url):
        q = self.session.query(SQLPage).filter_by(url=url)
        page = q.first()
        if page is None:
            return None
        return SQLDatabasePage(self.wiki, db_obj=page)

    def _getPageByPath(self, path):
        q = self.session.query(SQLPage).filter_by(path=path)
        page = q.first()
        if page is None:
            return None
        return SQLDatabasePage(self.wiki, db_obj=page)

    def _createSchema(self):
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

    def _cacheExtendedData(self, page):
        logger.info("Caching extended data for page '%s' [%d]." % (page.url, page._id))

        if not hasattr(page, '_id') or not page._id:
            raise Exception("Given page '%s' has no `_id` attribute set." % page.url)
        db_obj = self.session.query(SQLPage).filter(SQLPage.id == page._id).one()

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


    def _removePage(self, page):
        logger.debug("Removing page '%s' [%d] from SQL database." %
            (page.url, page.id))
        self.session.delete(page)


class SQLDatabasePage(Page):
    """ A page that can load its properties from a database.
    """
    def __init__(self, wiki, url=None, db_obj=None):
        if url and db_obj:
            raise Exception("You can't specify both an url and a database object.")
        if not url and not db_obj:
            raise Exception("You need to specify either a url or a database object.")

        super(SQLDatabasePage, self).__init__(wiki, url or db_obj.url)
        self.auto_update = wiki.config.getboolean('wiki', 'auto_update')
        self._db_obj = db_obj

    @property
    def path(self):
        if self._db_obj:
            return self._db_obj.path
        return super(SQLDatabasePage, self).path

    @property
    def _id(self):
        if self._db_obj:
            return self._db_obj.id
        self._ensureData()
        return self._data._db_id

    def _loadData(self):
        try:
            db_obj = self._db_obj or self.wiki.db.getPage(self.url)
        except PageNotFoundError:
            raise PageNotFoundError(self.url, "Please run `update` or `reset`.")
        data = self._loadFromDbObject(db_obj)
        self._db_obj = None
        return data

    def _onExtendedDataLoaded(self):
        self.wiki.db._cacheExtendedData(self)

    def _loadFromDbObject(self, db_obj, bypass_auto_update=False):
        if not bypass_auto_update and self.auto_update:
            path_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(db_obj.path))
            if path_time >= db_obj.time:
                logger.debug(
                    "Updating database cache for page '%s'." % self.url)
                try:
                    fs_page = FileSystemPage(self.wiki, self.url)
                    fs_page._ensureData()
                    added_ids = self.wiki.db.update([fs_page])
                    if not added_ids:
                        raise Exception("Page '%s' has been updated, but the database can't find it." % self.url)
                    fs_page._data._db_id = added_ids[0]
                    return fs_page._data
                except Exception as e:
                    msg = "Error updating database cache from the file-system: %s" % e
                    raise PageLoadingError(msg, e)

        data = PageData()
        data._db_id = db_obj.id
        data.path = db_obj.path
        split = os.path.splitext(data.path)
        data.filename = split[0]
        data.extension = split[1].lstrip('.')
        data.title = db_obj.title
        data.raw_text = db_obj.raw_text
        data.formatted_text = db_obj.formatted_text

        data.local_meta = {}
        for m in db_obj.meta:
            value = data.local_meta.get(m.name)
            if m.name in SINGLE_METAS:
                data.local_meta[m.name] = m.value
            else:
                if value is None:
                    data.local_meta[m.name] = [m.value]
                else:
                    data.local_meta[m.name].append(m.value)

        data.local_links = [l.target_url for l in db_obj.links]

        if db_obj.is_ready and not self._force_resolve:
            # If we have extended cache data from the database, we might as
            # well load it now too.
            data.text = db_obj.ready_text
            for m in db_obj.ready_meta:
                value = data.ext_meta.get(m.name)
                if value is None:
                    data.ext_meta[m.name] = [m.value]
                else:
                    data.ext_meta[m.name].append(m.value)
            data.ext_links = [l.target_url for l in db_obj.ready_links]
            # Flag this data as completely loaded.
            data.has_extended_data = True

        return data

