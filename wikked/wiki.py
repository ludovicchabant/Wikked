import os
import os.path
import time
import logging
import importlib
import multiprocessing
from configparser import SafeConfigParser, NoOptionError
from wikked.page import FileSystemPage
from wikked.fs import FileSystem
from wikked.auth import UserManager
from wikked.scheduler import ResolveScheduler


logger = logging.getLogger(__name__)


def passthrough_formatter(text):
    """ Passthrough formatter. Pretty simple stuff. """
    return text


class InitializationError(Exception):
    """ An exception that can get raised while the wiki gets
        initialized.
    """
    pass


NORMAL_CONTEXT = 0
INIT_CONTEXT = 1
BACKGROUND_CONTEXT = 2


def synchronous_wiki_updater(wiki, url):
    wiki.updateAll()


class WikiParameters(object):
    """ An object that defines how a wiki gets initialized.
    """
    def __init__(self, root=None, ctx=NORMAL_CONTEXT):
        if root is None:
            root = os.getcwd()
        self.root = root
        self.context = ctx
        self.formatters = self.getFormatters()
        self.wiki_updater = synchronous_wiki_updater
        self._config = None
        self._index_factory = None
        self._scm_factory = None

    @property
    def config(self):
        if self._config is None:
            self._config = self._loadConfig()
        return self._config

    def fs_factory(self):
        return FileSystem(self.root, self.config)

    def index_factory(self):
        self._ensureIndexFactory()
        return self._index_factory()

    def db_factory(self):
        from wikked.db.sql import SQLDatabase
        return SQLDatabase(self.config)

    def scm_factory(self):
        self._ensureScmFactory()
        return self._scm_factory()

    def auth_factory(self):
        return UserManager(self.config)

    def getFormatters(self):
        formatters = {passthrough_formatter: ['txt', 'html']}
        self.tryAddFormatter(formatters, 'markdown', 'markdown',
                             ['md', 'mdown', 'markdown'])
        self.tryAddFormatter(formatters, 'textile', 'textile',
                             ['tl', 'text', 'textile'])
        self.tryAddFormatter(formatters, 'creole', 'creole2html',
                             ['cr', 'creole'])
        return formatters

    def getSpecialFilenames(self):
        yield '.wikirc'
        yield '.wiki'
        yield '_files'
        if self.config.has_section('ignore'):
            for name, val in self.config.items('ignore'):
                yield val

    def tryAddFormatter(self, formatters, module_name, module_func,
                        extensions):
        try:
            module = importlib.import_module(module_name)
            func = getattr(module, module_func)
            formatters[func] = extensions
        except ImportError:
            pass

    def _loadConfig(self):
        # Merge the default settings with any settings provided by
        # the local config file(s).
        config_path = os.path.join(self.root, '.wikirc')
        local_config_path = os.path.join(self.root, '.wiki', 'wikirc')
        default_config_path = os.path.join(
            os.path.dirname(__file__), 'resources', 'defaults.cfg')

        config = SafeConfigParser()
        config.readfp(open(default_config_path))
        config.set('wiki', 'root', self.root)
        config.read([config_path, local_config_path])
        return config

    def _ensureIndexFactory(self):
        if self._index_factory is None:
            index_type = self.config.get('wiki', 'indexer')
            if index_type == 'whoosh':
                def impl():
                    from wikked.indexer.whooshidx import WhooshWikiIndex
                    return WhooshWikiIndex()
                self._index_factory = impl
            elif index_type == 'elastic':
                def impl():
                    from wikked.indexer.elastic import ElasticWikiIndex
                    return ElasticWikiIndex()
                self._index_factory = impl
            else:
                raise InitializationError("No such indexer: " + index_type)

    def _ensureScmFactory(self):
        if self._scm_factory is None:
            try:
                scm_type = self.config.get('wiki', 'sourcecontrol')
            except NoOptionError:
                # Auto-detect
                if os.path.isdir(os.path.join(self.root, '.hg')):
                    scm_type = 'hg'
                elif os.path.isdir(os.path.join(self.root, '.git')):
                    scm_type = 'git'
                else:
                    # Default to Mercurial. Yes. I just decided that myself.
                    scm_type = 'hg'

            if self.context == INIT_CONTEXT and scm_type == 'hg':
                # Quick workaround for when we're creating a new repo,
                # or running background tasks.
                # We'll be using the `hg` process instead of the command
                # server, since there's no repo there yet, or we just don't
                # want to spawn a new process unless we want to.
                logger.debug("Forcing `hgexe` source-control for new repo.")
                scm_type = 'hgexe'

            if scm_type == 'hg':
                def impl():
                    from wikked.scm.mercurial import MercurialCommandServerSourceControl
                    return MercurialCommandServerSourceControl(self.root)
                self._scm_factory = impl

            elif scm_type == 'hgexe':
                def impl():
                    from wikked.scm.mercurial import MercurialSourceControl
                    return MercurialSourceControl(self.root)
                self._scm_factory = impl

            elif scm_type == 'git':
                def impl():
                    from wikked.scm.git import GitLibSourceControl
                    return GitLibSourceControl(self.root)
                self._scm_factory = impl
            else:
                raise InitializationError(
                    "No such source control: " + scm_type)


class EndpointInfo(object):
    def __init__(self, name):
        self.name = name
        self.query = True
        self.default = None


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

        self.formatters = parameters.formatters
        self.special_filenames = parameters.getSpecialFilenames()

        self.main_page_url = (
            '/' +
            parameters.config.get('wiki', 'main_page').strip('/'))
        self.templates_url = (
            parameters.config.get('wiki', 'templates_endpoint') +
            ':/')
        self.endpoints = self._createEndpointInfos(parameters.config)

        self.fs = parameters.fs_factory()
        self.index = parameters.index_factory()
        self.db = parameters.db_factory()
        self.scm = parameters.scm_factory()
        self.auth = parameters.auth_factory()

        self._wiki_updater = parameters.wiki_updater
        self.post_update_hooks = []

    @property
    def root(self):
        return self.fs.root

    def start(self, update=False):
        """ Properly initializes the wiki and all its sub-systems.
        """
        order = [self.fs, self.scm, self.index, self.db, self.auth]
        for o in order:
            o.start(self)

        if update:
            self.updateAll()

    def init(self):
        """ Creates a new wiki at the specified root directory.
        """
        order = [self.fs, self.scm, self.index, self.db, self.auth]
        for o in order:
            o.init(self)
        self.start()
        for o in order:
            o.postInit()

    def stop(self, exception=None):
        """ De-initializes the wiki and its sub-systems.
        """
        self.db.close(exception)

    def reset(self, parallel=False):
        """ Clears all the cached data and rebuilds it from scratch.
        """
        logger.info("Resetting wiki data...")
        page_infos = self.fs.getPageInfos()
        self.db.reset(page_infos)
        self.resolve(force=True, parallel=parallel)
        self.index.reset(self.getPages())

    def resolve(self, only_urls=None, force=False, parallel=False):
        """ Compute the final info (text, meta, links) of all or a subset of
            the pages, and caches it in the DB.
        """
        logger.debug("Resolving pages...")
        if only_urls:
            page_urls = only_urls
        else:
            page_urls = self.db.getPageUrls(uncached_only=(not force))

        num_workers = multiprocessing.cpu_count() if parallel else 1
        s = ResolveScheduler(self, page_urls)
        s.run(num_workers)

    def updatePage(self, url=None, path=None):
        """ Completely updates a single page, i.e. read it from the file-system
            and have it fully resolved and cached in the DB.
        """
        if url and path:
            raise Exception("Can't specify both an URL and a path.")
        logger.info("Updating page: %s" % (url or path))
        if path:
            page_info = self.fs.getPageInfo(path)
        else:
            page_info = self.fs.findPageInfo(url)
        self.db.updatePage(page_info)
        self.resolve(only_urls=[page_info.url])
        self.index.updatePage(self.db.getPage(
            page_info.url,
            fields=['url', 'path', 'title', 'text']))

    def updateAll(self, parallel=False):
        """ Completely updates all pages, i.e. read them from the file-system
            and have them fully resolved and cached in the DB.
            This function will check for timestamps to only update pages that
            need it.
        """
        logger.info("Updating all pages...")
        page_infos = self.fs.getPageInfos()
        self.db.updateAll(page_infos)
        self.resolve(parallel=parallel)
        self.index.updateAll(self.db.getPages(
            fields=['url', 'path', 'title', 'text']))

    def getPageUrls(self, subdir=None):
        """ Returns all the page URLs in the wiki, or in the given
            sub-directory.
        """
        for url in self.db.getPageUrls(subdir):
            yield url

    def getPages(self, subdir=None, meta_query=None,
                 endpoint_only=None, no_endpoint_only=False, fields=None):
        """ Gets all the pages in the wiki, or in the given sub-directory.
        """
        for page in self.db.getPages(subdir=subdir, meta_query=meta_query,
                endpoint_only=endpoint_only, no_endpoint_only=no_endpoint_only,
                fields=fields):
            yield page

    def getPage(self, url, fields=None):
        """ Gets the page for a given URL.
        """
        return self.db.getPage(url, fields=fields)

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
            'message': page_fields['message']}
        self.scm.commit([page_info.path], commit_meta)

        # Update the DB and index with the new/modified page.
        self.updatePage(path=page_info.path)

        # Invalidate all page lists.
        self.db.removeAllPageLists()

        # Update all the other pages.
        self._wiki_updater(self, url)
        for hook in self.post_update_hooks:
            hook(self, url)

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
            'message': page_fields['message']}
        self.scm.commit([path], commit_meta)

        # Update the DB and index with the modified page.
        self.updatePage(url)

        # Update all the other pages.
        self._wiki_updater(self, url)
        for hook in self.post_update_hooks:
            hook(self, url)

    def pageExists(self, url):
        """ Returns whether a page exists at the given URL.
        """
        return self.db.pageExists(url)

    def getHistory(self, limit=10, after_rev=None):
        """ Shorthand method to get the history from the source-control.
        """
        return self.scm.getHistory(limit=limit, after_rev=after_rev)

    def getSpecialFilenames(self):
        return self.special_filenames

    def _createEndpointInfos(self, config):
        endpoints = {}
        sections = [s for s in config.sections() if s.startswith('endpoint:')]
        for s in sections:
            ep = EndpointInfo(s[9:])   # 9 = len('endpoint:')
            if config.has_option(s, 'query'):
                ep.query = config.getboolean(s, 'query')
            if config.has_option(s, 'default'):
                ep.default = config.get(s, 'default')
            endpoints[ep.name] = ep
        return endpoints


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
                print("Change detected in '%s'." % path)
        time.sleep(interval)
