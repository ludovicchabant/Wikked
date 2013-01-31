import os
import os.path
import time
import logging
import itertools
from ConfigParser import SafeConfigParser
import markdown
import textile
import creole
from page import Page, DatabasePage
from fs import FileSystem
from db import SQLiteDatabase, conn_scope
from scm import MercurialSourceControl
from indexer import WhooshWikiIndex
from auth import UserManager


def passthrough_formatter(text):
    """ Passthrough formatter. Pretty simple stuff.
    """
    return text


class InitializationError(Exception):
    """ An exception that can get raised while the wiki gets
        initialized.
    """
    pass


class WikiParameters(object):
    """ An object that defines how a wiki gets initialized.
    """
    def __init__(self, root=None):
        if root is None:
            root = os.getcwd()
        self.root = root

        self.formatters = {
            markdown.markdown: ['md', 'mdown', 'markdown'],
            textile.textile: ['tl', 'text', 'textile'],
            creole.creole2html: ['cr', 'creole'],
            passthrough_formatter: ['txt', 'html']
        }
        self.config_path = os.path.join(self.root, '.wikirc')
        self.index_path = os.path.join(self.root, '.wiki', 'index')
        self.db_path = os.path.join(self.root, '.wiki', 'wiki.db')

        self.use_db = True
        self.page_factory = DatabasePage.factory

    def logger_factory(self):
        if getattr(self, 'logger', None):
            return self.logger
        return logging.getLogger('wikked.wiki')

    def config_factory(self):
        return open(self.config_path)

    def fs_factory(self, config):
        return FileSystem(self.root, slugify=Page.title_to_url, logger=self.logger_factory())

    def index_factory(self, config):
        return WhooshWikiIndex(self.index_path, logger=self.logger_factory())

    def db_factory(self, config):
        return SQLiteDatabase(self.db_path, logger=self.logger_factory())

    def scm_factory(self, config):
        scm_type = config.get('wiki', 'scm')
        if scm_type == 'hg':
            return MercurialSourceControl(self.root, logger=self.logger_factory())
        else:
            raise InitializationError("No such source control: " + scm_type)

    def getSpecialFilenames(self):
        yield self.config_path
        yield os.path.join(self.root, '.wiki')


class Wiki(object):
    """ The wiki class! This is where the magic happens.
    """
    def __init__(self, parameters):
        """ Creates a new wiki instance. It won't be fully functional
            until you call `start`, which does the actual initialization.
            This gives you a chance to customize a few more things before
            getting started.
        """
        if parameters is None:
            raise ValueError("No parameters were given to the wiki.")

        self.logger = parameters.logger_factory()
        self.logger.debug("Initializing wiki.")

        self.config = self._loadConfig(parameters)

        self.formatters = parameters.formatters
        self.use_db = parameters.use_db
        self.page_factory = DatabasePage.factory

        self.fs = parameters.fs_factory(self.config)
        self.index = parameters.index_factory(self.config)
        self.db = parameters.db_factory(self.config)
        self.scm = parameters.scm_factory(self.config)

        self.auth = UserManager(self.config, logger=self.logger)

        self.fs.page_extensions = list(set(
            itertools.chain(*self.formatters.itervalues())))
        self.fs.excluded += parameters.getSpecialFilenames()
        self.fs.excluded += self.scm.getSpecialFilenames()

    def start(self, update=True):
        """ Properly initializes the wiki and all its sub-systems.
        """
        self.scm.initRepo()
        self.index.initIndex()
        self.db.initDb()

        if update:
            with conn_scope(self.db):
                self.db.update(self.getPages(from_db=False, factory=Page.factory))
                self.index.update(self.getPages())

    def stop(self):
        self.db.close()

    def getPageUrls(self, subdir=None, from_db=None):
        """ Returns all the page URLs in the wiki, or in the given
            sub-directory.
            By default, it queries the DB, but it can query the file-system
            directly if `from_db` is `False`.
        """
        if from_db is None:
            from_db = self.use_db
        if from_db:
            for url in self.db.getPageUrls(subdir):
                yield url
        else:
            for info in self.fs.getPageInfos(subdir):
                yield info['url']

    def getPages(self, subdir=None, from_db=None, factory=None):
        """ Gets all the pages in the wiki, or in the given sub-directory.
            By default it will use the DB to fetch the list of pages, but it
            can scan the file-system directly if `from_db` is `False`. If
            that's the case, it's probably a good idea to provide a custom
            `factory` for creating `Page` instances, since by default it will
            use `DatabasePage` which also uses the DB to load its information.
        """
        if from_db is None:
            from_db = self.use_db
        if factory is None:
            factory = self.page_factory
        for url in self.getPageUrls(subdir, from_db):
            yield factory(self, url)

    def getPage(self, url, factory=None):
        """ Gets the page for a given URL.
        """
        if factory is None:
            factory = self.page_factory
        return factory(self, url)

    def setPage(self, url, page_fields):
        """ Updates or creates a page for a given URL.
        """
        # Validate the parameters.
        if 'author' not in page_fields:
            raise ValueError(
                "No author specified for editing page '%s'." % url)
        if 'message' not in page_fields:
            raise ValueError(
                "No commit message specified for editing page '%s'." % url)

        # Save the new/modified text.
        do_commit = False
        path = self.fs.getPhysicalPagePath(url)
        if 'text' in page_fields:
            self.fs.setPage(path, page_fields['text'])
            do_commit = True

        # Commit the file to the source-control.
        if do_commit:
            commit_meta = {
                    'author': page_fields['author'],
                    'message': page_fields['message']
                    }
            self.scm.commit([path], commit_meta)

        # Update the DB and index with the new/modified page.
        self.db.update([self.getPage(url)])
        self.index.update([self.getPage(url)])

    def pageExists(self, url, from_db=None):
        """ Returns whether a page exists at the given URL.
            By default it will query the DB, but it can query the underlying
            file-system directly if `from_db` is `False`.
        """
        if from_db is None:
            from_db = self.use_db
        if from_db:
            return self.db.pageExists(url)
        return self.fs.pageExists(url)

    def getHistory(self):
        """ Shorthand method to get the history from the source-control.
        """
        return self.scm.getHistory()

    def _loadConfig(self, parameters):
        # Merge the default settings with any settings provided by
        # the parameters.
        default_config_path = os.path.join(
            os.path.dirname(__file__), 'resources', 'defaults.cfg')
        config = SafeConfigParser()
        config.readfp(open(default_config_path))

        fp = parameters.config_factory()
        config.readfp(fp)
        fp.close()

        return config


def reloader_stat_loop(wiki, interval=1):
    mtimes = {}
    while 1:
        for page_info in wiki.fs.getPageInfos():
            path = page_info['path']
            try:
                mtime = os.stat(path).st_mtime
            except OSError:
                continue

            old_time = mtimes.get(path)
            if old_time is None:
                mtimes[path] = mtime
                continue
            elif mtime > old_time:
                print "Change detected in '%s'." % path
        time.sleep(interval)
