import os
import os.path
import types
import string
import logging
import datetime
from sqlalchemy import (
        and_,
        Column, Boolean, Integer, String, Text, DateTime, ForeignKey)
from sqlalchemy.orm import relationship, backref, defer
from wikked.web import db


class Database(object):
    """ The base class for a database cache.
    """
    def __init__(self, logger=None):
        if logger is None:
            logger = logging.getLogger('wikked.db')
        self.logger = logger

    def initDb(self):
        raise NotImplementedError()

    def open(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def reset(self, pages):
        raise NotImplementedError()

    def update(self, pages, force=False):
        raise NotImplementedError()

    def getPageUrls(self, subdir=None):
        raise NotImplementedError()

    def getPages(self, subdir=None, meta_query=None):
        raise NotImplementedError()

    def getPage(self, url=None, path=None):
        raise NotImplementedError()

    def pageExists(self, url=None, path=None):
        raise NotImplementedError()

    def getLinksTo(self, url):
        raise NotImplementedError()


Base = db.Model

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

    def __init__(self, db_path, logger=None):
        Database.__init__(self, logger)
        self.db_path = db_path

    def initDb(self):
        create_schema = False
        if self.db_path != 'sqlite:///:memory:':
            if not os.path.exists(os.path.dirname(self.db_path)):
                # No database on disk... create one.
                self.logger.debug("Creating SQL database at: %s" % self.db_path)
                create_schema = True
            else:
                # The existing schema is outdated, re-create it.
                schema_version = self._getSchemaVersion()
                if schema_version < self.schema_version:
                    self.logger.debug(
                            "SQL database is outdated (got version %s), will re-create.",
                            schema_version)
                    create_schema = True
                else:
                    self.logger.debug(
                            "SQL database has up-to-date schema.")
        else:
            create_schema = True
        if create_schema:
            self._createSchema()

    def open(self):
        self.logger.debug("Opening connection")

    def close(self):
        self.logger.debug("Closing connection")

    def reset(self, pages):
        self.logger.debug("Re-creating SQL database.")
        self._createSchema()
        for page in pages:
            self._addPage(page)
        db.session.commit()

    def update(self, pages, force=False):
        to_update = set()
        already_added = set()
        to_remove = []
        pages = list(pages)

        self.logger.debug("Updating SQL database...")
        page_urls = [p.url for p in pages]
        db_pages = db.session.query(SQLPage).\
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

        db.session.commit()

        added_db_objs = []
        for p in pages:
            if (p.path in to_update or
                p.path not in already_added):
                added_db_objs.append(self._addPage(p))

        db.session.commit()

        if to_remove or added_db_objs:
            db_pages = db.session.query(SQLPage).\
                    options(
                            defer(SQLPage.title),
                            defer(SQLPage.raw_text),
                            defer(SQLPage.formatted_text),
                            defer(SQLPage.ready_text)).\
                    all()
            for p in db_pages:
                p.is_ready = False
            
            db.session.commit()

        self.logger.debug("...done updating SQL database.")
        return [o.id for o in added_db_objs]

    def getPageUrls(self, subdir=None):
        q = db.session.query(SQLPage.url)
        if subdir:
            subdir = string.rstrip(subdir, '/') + '/%'
            q = q.filter(SQLPage.url.like(subdir))
        urls = []
        for p in q.all():
            urls.append(p.url)
        return urls

    def getPages(self, subdir=None, meta_query=None):
        q = db.session.query(SQLPage)
        if meta_query:
            q = q.join(SQLReadyMeta)
            for name, values in meta_query.iteritems():
                for v in values:
                    q = q.filter(and_(SQLReadyMeta.name == name, SQLReadyMeta.value == v))
        if subdir:
            subdir = string.rstrip(subdir, '/') + '/%'
            q = q.filter(SQLPage.url.like(subdir))
        pages = []
        for p in q.all():
            pages.append(p)
        return pages

    def getPage(self, url=None, path=None):
        if not url and not path:
            raise ValueError("Either URL or path need to be specified.")
        if url and path:
            raise ValueError("Can't specify both URL and path.")
        if url:
            q = db.session.query(SQLPage).filter_by(url=url)
            page = q.first()
            return page
        if path:
            q = db.session.query(SQLPage).filter_by(path=path)
            page = q.first()
            return page

    def pageExists(self, url=None, path=None):
        return self.getPage(url, path) is not None

    def getLinksTo(self, url):
        q = db.session.query(SQLReadyLink).\
            filter(SQLReadyLink.target_url == url).\
            join(SQLReadyLink.source).\
            all()
        for l in q:
            yield l.source.url

    def _createSchema(self):
        db.drop_all()
        db.create_all()

        ver = SQLInfo()
        ver.name = 'schema_version'
        ver.int_value = self.schema_version
        db.session.add(ver)
        db.session.commit()

    def _getSchemaVersion(self):
        try:
            q = db.session.query(SQLInfo).\
                    filter(SQLInfo.name == 'schema_version').\
                    first()
            if q is None:
                return 0
        except:
            return -1
        return q.int_value

    def _addPage(self, page):
        self.logger.debug("Adding page '%s' to SQL database." % page.url)

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

        db.session.add(po)

        return po

    def _cacheExtendedData(self, page):
        self.logger.debug("Caching extended data for page '%s' [%d]." % (page.url, page._id))

        if not hasattr(page, '_id') or not page._id:
            raise Exception("Given page '%s' has no `_id` attribute set." % page.url)
        db_obj = db.session.query(SQLPage).filter(SQLPage.id == page._id).one()

        db_obj.ready_text = page._data.text
        db_obj.is_ready = True
        
        for name, value in page._data.ext_meta.iteritems():
            if isinstance(value, bool):
                value = ""
            if isinstance(value, types.StringTypes):
                db_obj.ready_meta.append(SQLReadyMeta(name, value))
            else:
                for v in value:
                    db_obj.ready_meta.append(SQLReadyMeta(name, v))

        for link_url in page._data.ext_links:
            db_obj.ready_links.append(SQLReadyLink(link_url))

        db.session.commit()


    def _removePage(self, page):
        self.logger.debug("Removing page '%s' [%d] from SQL database." %
            (page.url, page.id))
        db.session.delete(page)

