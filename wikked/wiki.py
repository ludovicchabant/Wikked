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
from cache import Cache
from fs import FileSystem
from db import SQLiteDatabase
from scm import MercurialSourceControl
from indexer import WhooshWikiIndex
from auth import UserManager


class InitializationError(Exception):
    pass


class Wiki(object):
    def __init__(self, root=None, logger=None):
        if root is None:
            root = os.getcwd()

        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger('wikked.wiki')
        self.logger.debug("Initializing wiki at: " + root)

        self.page_factory = DatabasePage.factory
        self.use_db = True
        self.formatters = {
                markdown.markdown: ['md', 'mdown', 'markdown'],
                textile.textile: ['tl', 'text', 'textile'],
                creole.creole2html: ['cr', 'creole'],
                self._passthrough: ['txt', 'html']
                }

        self.default_config_path = os.path.join(
            os.path.dirname(__file__), 'resources', 'defaults.cfg')
        self.config_path = os.path.join(root, '.wikirc')
        self.config = self._loadConfig()

        self.fs = FileSystem(root, slugify=Page.title_to_url)
        self.auth = UserManager(self.config, logger=self.logger)
        self.index = WhooshWikiIndex(os.path.join(root, '.wiki', 'index'),
            logger=self.logger)
        self.db = SQLiteDatabase(self, logger=self.logger)
        self.scm = self._createScm()
        self.cache = self._createJsonCache()

        self.fs.page_extensions = list(set(
            itertools.chain(*self.formatters.itervalues())))
        self.fs.excluded.append(self.config_path)
        self.fs.excluded.append(os.path.join(root, '.wiki'))
        if self.scm is not None:
            self.fs.excluded += self.scm.getSpecialDirs()

    def _createScm(self):
        scm_type = self.config.get('wiki', 'scm')
        if scm_type == 'hg':
            return MercurialSourceControl(self.fs.root, self.logger)
        else:
            raise InitializationError("No such source control: " + scm_type)

    def _createJsonCache(self):
        if (not self.config.has_option('wiki', 'cache') or
                self.config.getboolean('wiki', 'cache')):
            return Cache(os.path.join(self.fs.root, '.wiki', 'cache'))
        else:
            return None

    def _loadConfig(self):
        config = SafeConfigParser()
        config.readfp(open(self.default_config_path))
        config.read(self.config_path)
        return config

    def start(self, update=True):
        if self.scm is not None:
            self.scm.initRepo()
        if self.index is not None:
            self.index.initIndex()
        if self.db is not None:
            self.db.initDb()

        if update:
            pass

    @property
    def root(self):
        return self.fs.root

    def getPageUrls(self, subdir=None, from_db=True):
        if from_db and self.db:
            for url in self.db.getPageUrls(subdir):
                yield url
        else:
            for info in self.fs.getPageInfos(subdir):
                yield info['url']

    def getPages(self, subdir=None, from_db=True, factory=None):
        if factory is None:
            factory = self.page_factory
        for url in self.getPageUrls(subdir, from_db):
            yield factory(self, url)

    def getPage(self, url, factory=None):
        if factory is None:
            factory = self.page_factory
        return factory(self, url)

    def setPage(self, url, page_fields):
        if 'author' not in page_fields:
            raise ValueError(
                "No author specified for editing page '%s'." % url)
        if 'message' not in page_fields:
            raise ValueError(
                "No commit message specified for editing page '%s'." % url)

        do_commit = False
        path = self.fs.getPhysicalPagePath(url)

        if 'text' in page_fields:
            with open(path, 'w') as f:
                f.write(page_fields['text'])
            do_commit = True

        if do_commit:
            commit_meta = {
                    'author': page_fields['author'],
                    'message': page_fields['message']
                    }
            self.scm.commit([path], commit_meta)

        if self.db is not None:
            self.db.update([self.getPage(url)])
        if self.index is not None:
            self.index.update([self.getPage(url)])

    def pageExists(self, url, from_db=True):
        if from_db:
            return self.db.pageExists(url)
        return self.fs.pageExists(url)

    def getHistory(self):
        return self.scm.getHistory()

    def _passthrough(self, content):
        return content


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
