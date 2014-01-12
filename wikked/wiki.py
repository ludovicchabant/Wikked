import os
import os.path
import time
import logging
import importlib
from ConfigParser import SafeConfigParser, NoOptionError
from wikked.page import FileSystemPage
from wikked.fs import FileSystem
from wikked.auth import UserManager


logger = logging.getLogger(__name__)


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

    def fs_factory(self, config):
        return FileSystem(self.root)

    def index_factory(self, config):
        index_type = config.get('wiki', 'indexer')
        if index_type == 'whoosh':
            from wikked.indexer.whooshidx import WhooshWikiIndex
            return WhooshWikiIndex()
        elif index_type == 'elastic':
            from wikked.indexer.elastic import ElasticWikiIndex
            return ElasticWikiIndex()
        else:
            raise InitializationError("No such indexer: " + index_type)

    def db_factory(self, config):
        from wikked.db.sql import SQLDatabase
        return SQLDatabase()

    def scm_factory(self, config):
        try:
            scm_type = config.get('wiki', 'sourcecontrol')
        except NoOptionError:
            # Auto-detect
            if os.path.isdir(os.path.join(self.root, '.hg')):
                scm_type = 'hg'
            elif os.path.isdir(os.path.join(self.root, '.git')):
                scm_type = 'git'
            else:
                # Default to Mercurial. Yes. I just decided that myself.
                scm_type = 'hg'

        if scm_type == 'hg':
            from wikked.scm.mercurial import MercurialCommandServerSourceControl
            return MercurialCommandServerSourceControl(self.root)
        elif scm_type == 'git':
            from wikked.scm.git import GitLibSourceControl
            return GitLibSourceControl(self.root)
        else:
            raise InitializationError("No such source control: " + scm_type)

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

        logger.debug("Initializing wiki.")


        self.parameters = parameters
        self.config = self._loadConfig(parameters)
        self.main_page_url = '/' + self.config.get('wiki', 'main_page').strip('/')
        self.templates_url = '/' + self.config.get('wiki', 'templates_dir').strip('/') + '/'

        self.formatters = parameters.formatters

        self.fs = parameters.fs_factory(self.config)
        self.index = parameters.index_factory(self.config)
        self.db = parameters.db_factory(self.config)
        self.scm = parameters.scm_factory(self.config)

        self.auth = UserManager(self.config)

        if self.config.getboolean('wiki', 'async_updates'):
            logger.debug("Setting up asynchronous updater.")
            from tasks import update_wiki
            self._updateSetPage = lambda url: update_wiki.delay(self.root)
        else:
            logger.debug("Setting up simple updater.")
            self._updateSetPage = lambda url: self.update(url, cache_ext_data=False)

    @property
    def root(self):
        return self.fs.root

    def start(self, update=True):
        """ Properly initializes the wiki and all its sub-systems.
        """
        self.fs.initFs(self)
        self.scm.initRepo(self)
        self.index.initIndex(self)
        self.db.initDb(self)

        if update:
            self.update()

    def stop(self):
        self.db.close()

    def reset(self, cache_ext_data=True):
        logger.debug("Resetting wiki data...")
        page_infos = self.fs.getPageInfos()
        fs_pages = FileSystemPage.fromPageInfos(self, page_infos)
        self.db.reset(fs_pages)
        self.index.reset(self.getPages())

        if cache_ext_data:
            self._cachePages()

    def update(self, url=None, cache_ext_data=True):
        updated_urls = []
        logger.debug("Updating pages...")
        if url:
            page_info = self.fs.getPage(url)
            fs_page = FileSystemPage(self, page_info=page_info)
            self.db.update([fs_page], force=True)
            updated_urls.append(url)
            self.index.update([self.getPage(url)])
        else:
            page_infos = self.fs.getPageInfos()
            fs_pages = FileSystemPage.fromPageInfos(self, page_infos)
            self.db.update(fs_pages)
            updated_urls += [p.url for p in fs_pages]
            self.index.update(self.getPages())

        if cache_ext_data:
            self._cachePages([url] if url else None)

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
            yield page

    def getPage(self, url):
        """ Gets the page for a given URL.
        """
        return self.db.getPage(url)

    def setPage(self, url, page_fields, do_update=True):
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
        if do_update:
            self._updateSetPage(url)

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
        self.fs.setPage(url, rev_text)

        # Commit to source-control.
        commit_meta = {
                'author': page_fields['author'],
                'message': page_fields['message']
                }
        self.scm.commit([path], commit_meta)

        # Update the DB and index with the modified page.
        self.update(url, cache_ext_data=False)

    def pageExists(self, url):
        """ Returns whether a page exists at the given URL.
        """
        return self.db.pageExists(url)

    def getHistory(self, limit=10):
        """ Shorthand method to get the history from the source-control.
        """
        return self.scm.getHistory(limit=limit)

    def getSpecialFilenames(self):
        yield '.wikirc'
        yield '.wiki'
        if self.config.has_section('ignore'):
            for name, val in self.config.items('ignore'):
                yield val

    def _cachePages(self, only_urls=None):
        logger.debug("Caching extended page data...")
        if only_urls:
            for url in only_urls:
                page = self.getPage(url)
                page._ensureExtendedData()
        else:
            for page in self.db.getUncachedPages():
                page._ensureExtendedData()

    def _loadConfig(self, parameters):
        # Merge the default settings with any settings provided by
        # the parameters.
        config_path = os.path.join(parameters.root, '.wikirc')
        local_config_path = os.path.join(parameters.root, '.wiki', 'wikirc')
        default_config_path = os.path.join(
            os.path.dirname(__file__), 'resources', 'defaults.cfg')

        config = SafeConfigParser()
        config.readfp(open(default_config_path))
        config.set('wiki', 'root', parameters.root)
        config.read([config_path, local_config_path])
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
