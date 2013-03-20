import os
import os.path
import types
import string
import logging
import datetime
import sqlite3


class conn_scope(object):
    """ Helper class, disguised as a function, to ensure the database
        has been opened before doing something. If the database wasn't
        open, it will be closed after the operation.
    """
    def __init__(self, db):
        self.db = db
        self.do_close = False

    def __enter__(self):
        self.do_close = (self.db.conn is None)
        self.db.open()

    def __exit__(self, type, value, traceback):
        if self.do_close:
            self.db.close()


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

    def update(self, pages):
        raise NotImplementedError()

    def getPageUrls(self, subdir=None):
        raise NotImplementedError()

    def getPages(self, subdir=None):
        raise NotImplementedError()

    def getPage(self, url):
        raise NotImplementedError()

    def pageExists(self, url):
        raise NotImplementedError()

    def getLinksTo(self, url):
        raise NotImplementedError()



class SQLitePageInfo(object):
    def __init__(self, row):
        self.url = row['url']
        self.path = row['path']
        self.time = row['time']
        self.title = row['title']
        self.raw_text = row['raw_text']
        self.formatted_text = row['formatted_text']
        self.links = []
        self.meta = {}


class SQLiteDatabase(Database):
    """ A database cache based on SQLite.
    """
    schema_version = 1

    def __init__(self, db_path, logger=None):
        Database.__init__(self, logger)
        self.db_path = db_path
        self.conn = None

    def initDb(self):
        create_schema = False
        if self.db_path != ':memory:':
            if not os.path.isdir(os.path.dirname(self.db_path)):
                # No database on disk... create one.
                self.logger.debug("Creating SQL database.")
                os.makedirs(os.path.dirname(self.db_path))
                create_schema = True
            else:
                # The existing schema is outdated, re-create it.
                schema_version = self._getSchemaVersion()
                if schema_version < self.schema_version:
                    create_schema = True
        else:
            create_schema = True
        if create_schema:
            with conn_scope(self):
                self._createSchema()

    def open(self):
        if self.conn is None:
            self.logger.debug("Opening connection")
            self.conn = sqlite3.connect(self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn is not None:
            self.logger.debug("Closing connection")
            self.conn.close()
            self.conn = None

    def reset(self, pages):
        self.logger.debug("Re-creating SQL database.")
        with conn_scope(self):
            self._createSchema()
            c = self.conn.cursor()
            for page in pages:
                self._addPage(page, c)
            self.conn.commit()

    def update(self, pages):
        self.logger.debug("Updating SQL database...")
        to_update = set()
        already_added = set()

        with conn_scope(self):
            c = self.conn.cursor()
            c.execute('''SELECT id, time, path FROM pages''')
            for r in c.fetchall():
                if not os.path.isfile(r['path']):
                    # File was deleted.
                    self._removePage(r['id'], c)
                else:
                    already_added.add(r['path'])
                    path_time = datetime.datetime.fromtimestamp(
                        os.path.getmtime(r['path']))
                    if path_time > r['time']:
                        # File has changed since last index.
                        self._removePage(r['id'], c)
                        to_update.add(r['path'])
            self.conn.commit()

            for page in pages:
                if (page.path in to_update or
                    page.path not in already_added):
                    self._addPage(page, c)

            self.conn.commit()
            self.logger.debug("...done updating SQL database.")

    def getPageUrls(self, subdir=None):
        with conn_scope(self):
            c = self.conn.cursor()
            if subdir:
                subdir = string.rstrip(subdir, '/') + '/%'
                c.execute('''SELECT url FROM pages WHERE url LIKE ?''',
                    (subdir,))
            else:
                c.execute('''SELECT url FROM pages''')
            urls = []
            for row in c.fetchall():
                urls.append(row['url'])
            return urls

    def getPages(self, subdir=None):
        with conn_scope(self):
            c = self.conn.cursor()
            if subdir:
                subdir = string.rstrip(subdir, '/') + '/%'
                c.execute('''SELECT id, url, path, time, title, raw_text,
                    formatted_text
                    FROM pages WHERE url LIKE ?''',
                    (subdir,))
            else:
                c.execute('''SELECT id, url, path, time, title, raw_text,
                    formatted_text
                    FROM pages''')
            pages = []
            for row in c.fetchall():
                pages.append(self._getPage(row, c))
            return pages

    def getPage(self, url):
        with conn_scope(self):
            c = self.conn.cursor()
            c.execute('''SELECT id, url, path, time, title, raw_text,
                formatted_text FROM pages WHERE url=?''', (url,))
            row = c.fetchone()
            if row is None:
                return None
            return self._getPage(row, c)

    def pageExists(self, url):
        with conn_scope(self):
            c = self.conn.cursor()
            c.execute('''SELECT id FROM pages WHERE url=?''', (url,))
            return c.fetchone() is not None

    def getLinksTo(self, url):
        with conn_scope(self):
            c = self.conn.cursor()
            c.execute('''SELECT source FROM links WHERE target=?''', (url,))
            sources = []
            for r in c.fetchall():
                sources.append(r['source'])
            return sources

    def _createSchema(self):
        self.logger.debug("Creating SQL schema...")
        c = self.conn.cursor()
        c.execute('''DROP TABLE IF EXISTS pages''')
        c.execute('''CREATE TABLE pages
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             time TIMESTAMP,
             url TEXT,
             path TEXT,
             title TEXT,
             raw_text TEXT,
             formatted_text TEXT)''')
        c.execute('''DROP TABLE IF EXISTS links''')
        c.execute('''CREATE TABLE links
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             source TEXT,
             target TEXT)''')
        c.execute('''DROP TABLE IF EXISTS meta''')
        c.execute('''CREATE TABLE meta
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             page_id INTEGER,
             name TEXT,
             value TEXT)''')
        c.execute('''DROP TABLE IF EXISTS info''')
        c.execute('''CREATE TABLE info
            (name TEXT UNIQUE NOT NULL,
             str_value TEXT,
             int_value INTEGER,
             time_value TIMESTAMP)''')
        c.execute('''INSERT INTO info (name, int_value) VALUES (?, ?)''',
            ('schema_version', self.schema_version))
        self.conn.commit()

    def _getInfo(self, name, default=None):
        with conn_scope(self):
            c = self.conn.cursor()
            c.execute('''SELECT name, str_value FROM info
                WHERE name=?''', (name,))
            row = c.fetchone()
            if row is None:
                return default
            return row['str_value']

    def _getInfoInt(self, name, default=None):
        with conn_scope(self):
            c = self.conn.cursor()
            c.execute('''SELECT name, int_value FROM info
                WHERE name=?''', (name,))
            row = c.fetchone()
            if row is None:
                return default
            return row['int_value']

    def _getInfoTime(self, name, default=None):
        with conn_scope(self):
            c = self.conn.cursor()
            c.execute('''SELECT name, time_value FROM info
                WHERE name=?''', (name,))
            row = c.fetchone()
            if row is None:
                return default
            return row['time_value']

    def _getSchemaVersion(self):
        with conn_scope(self):
            c = self.conn.cursor()
            c.execute('''SELECT name FROM sqlite_master
                WHERE type="table" AND name="info"''')
            if c.fetchone() is None:
                return 0
            c.execute('''SELECT int_value FROM info
                WHERE name="schema_version"''')
            row = c.fetchone()
            if row is None:
                return 0
            return row[0]

    def _addPage(self, page, c):
        self.logger.debug("Adding page '%s' to SQL database." % page.url)
        now = datetime.datetime.now()
        c.execute('''INSERT INTO pages
            (time, url, path, title, raw_text, formatted_text)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (now, page.url, page.path, page.title,
                page.raw_text, page._getFormattedText()))
        page_id = c.lastrowid

        for name, value in page._getLocalMeta().iteritems():
            if isinstance(value, bool):
                value = ""
            if isinstance(value, types.StringTypes):
                c.execute('''INSERT INTO meta
                    (page_id, name, value) VALUES (?, ?, ?)''',
                    (page_id, name, value))
            else:
                for v in value:
                    c.execute('''INSERT INTO meta
                        (page_id, name, value) VALUES (?, ?, ?)''',
                        (page_id, name, v))

        for link_url in page._getLocalLinks():
            c.execute('''INSERT INTO links
                (source, target) VALUES (?, ?)''',
                (page.url, link_url))

    def _removePage(self, page_id, c):
        c.execute('''SELECT url FROM pages WHERE id=?''', (page_id,))
        row = c.fetchone()
        self.logger.debug("Removing page '%s' [%d] from SQL database." %
            (row['url'], page_id))
        c.execute('''DELETE FROM pages WHERE id=?''', (page_id,))
        c.execute('''DELETE FROM meta WHERE page_id=?''', (page_id,))
        c.execute('''DELETE FROM links WHERE source=?''', (row['url'],))

    def _getPage(self, row, c):
        db_page = SQLitePageInfo(row)

        c.execute('''SELECT target FROM links
            WHERE source=?''', (row['url'],))
        for r in c.fetchall():
            db_page.links.append(r['target'])

        c.execute('''SELECT page_id, name, value
            FROM meta WHERE page_id=?''', (row['id'],))
        for r in c.fetchall():
            value = r['value']
            if value == '':
                value = True
            name = r['name']
            if name not in db_page.meta:
                db_page.meta[name] = [value]
            else:
                db_page.meta[name].append(value)

        return db_page
