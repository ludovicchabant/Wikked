import os
import os.path
import time
import logging
import itertools
import importlib
from ConfigParser import SafeConfigParser
from page import DatabasePage, FileSystemPage
from fs import FileSystem
from db import SQLDatabase
from scm import MercurialCommandServerSourceControl
from indexer import WhooshWikiIndex
from auth import UserManager


def passthrough_formatter(text):
    """ Passthrough formatter. Pretty simple stuff. """
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

        self.formatters = self.getFormatters()

        self.config_path = os.path.join(self.root, '.wikirc')
        self.index_path = os.path.join(self.root, '.wiki', 'index')
        self.db_path = os.path.join(self.root, '.wiki', 'wiki.db')

    def logger_factory(self):
        if getattr(self, 'logger', None):
            return self.logger
        return logging.getLogger(__name__)

    def config_factory(self):
        return open(self.config_path)

    def fs_factory(self, config):
        return FileSystem(self.root, logger=self.logger_factory())

    def index_factory(self, config):
        return WhooshWikiIndex(self.index_path, logger=self.logger_factory())

    def db_factory(self, config):
        return SQLDatabase(self.db_path, logger=self.logger_factory())

    def scm_factory(self, config):
        scm_type = config.get('wiki', 'scm')
        if scm_type == 'hg':
            return MercurialCommandServerSourceControl(self.root, logger=self.logger_factory())
        else:
            raise InitializationError("No such source control: " + scm_type)

    def getSpecialFilenames(self):
        yield self.config_path
        yield os.path.join(self.root, '.wiki')

    def getFormatters(self):
        formatters = {passthrough_formatter: ['txt', 'html']}
        self.tryAddFormatter(formatters, 'markdown', 'markdown', ['md', 'mdown', 'markdown'])
        self.tryAddFormatter(formatters, 'textile', 'textile', ['tl', 'text', 'textile'])
        self.tryAddFormatter(formatters, 'creole', 'creole2html', ['cr', 'creole'])
        return formatters

    def tryAddFormatter(self, formatters, module_name, module_func, extensions):
        try:
            module = importlib.import_module(module_name)
            func = getattr(module, module_func)
            formatters[func] = extensions
        except ImportError:
            pass


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
            page_infos = self.fs.getPageInfos()
            fs_pages = FileSystemPage.fromPageInfos(self, page_infos)
            self.db.update(fs_pages)
            self.index.update(self.getPages())

    def stop(self):
        self.db.close()

    def getPageUrls(self, subdir=None):
        """ Returns all the page URLs in the wiki, or in the given
            sub-directory.
        """
        for url in self.db.getPageUrls(subdir):
            yield url

    def getPages(self, subdir=None, meta_query=None):
        """ Gets all the pages in the wiki, or in the given sub-directory.
        """
        for page in self.db.getPages(subdir, meta_query):
            yield DatabasePage(self, db_obj=page)

    def getPage(self, url):
        """ Gets the page for a given URL.
        """
        return DatabasePage(self, url)

    def setPage(self, url, page_fields):
        """ Updates or creates a page for a given URL.
        """
        # Validate the parameters.
        if 'text' not in page_fields:
            raise ValueError(
                    "No text specified for editing page '%s'." % url)
        if 'author' not in page_fields:
            raise ValueError(
                    "No author specified for editing page '%s'." % url)
        if 'message' not in page_fields:
            raise ValueError(
                    "No commit message specified for editing page '%s'." % url)

        # Save the new/modified text.
        page_info = self.fs.setPage(url, page_fields['text'])

        # Commit the file to the source-control.
        commit_meta = {
                'author': page_fields['author'],
                'message': page_fields['message']
                }
        self.scm.commit([page_info.path], commit_meta)

        # Update the DB and index with the new/modified page.
        fs_page = FileSystemPage(self, page_info=page_info)
        self.db.update([fs_page])
        self.index.update([self.getPage(url)])

    def revertPage(self, url, page_fields):
        """ Reverts the page with the given URL to an older revision.
        """
        # Validate the parameters.
        if 'rev' not in page_fields:
            raise ValueError(
                    "No revision specified for reverting page '%s'." % url)
        if 'author' not in page_fields:
            raise ValueError(
                    "No author specified for reverting page '%s'." % url)
        if 'message' not in page_fields:
            raise ValueError(
                    "No commit message specified for reverting page '%s'." % url)

        # Get the revision.
        path = self.fs.getPhysicalPagePath(url)
        rev_text = self.scm.getRevision(path, page_fields['rev'])

        # Write to the file and commit.
        page_info = self.fs.setPage(url, rev_text)

        # Commit to source-control.
        commit_meta = {
                'author': page_fields['author'],
                'message': page_fields['message']
                }
        self.scm.commit([path], commit_meta)

        # Update the DB and index with the modified page.
        fs_page = FileSystemPage(self, page_info=page_info)
        self.db.update([fs_page])
        self.index.update([self.getPage(url)])

    def pageExists(self, url):
        """ Returns whether a page exists at the given URL.
        """
        return self.db.pageExists(url)

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
