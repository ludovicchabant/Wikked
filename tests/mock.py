import os
import os.path
import codecs
import logging
import io
from collections import deque
from contextlib import closing
from configparser import SafeConfigParser
from wikked.fs import FileSystem
from wikked.db.base import Database
from wikked.indexer.base import WikiIndex
from wikked.scm.base import SourceControl
from wikked.wiki import WikiParameters, passthrough_formatter


logger = logging.getLogger(__name__)


class MockWikiParameters(WikiParameters):
    def __init__(self, root=None):
        super(MockWikiParameters, self).__init__(root)
        self.config_text = ""
        self.mock_fs = None
        self.mock_index = None
        self.mock_db = None
        self.mock_scm = None

    def fs_factory(self):
        if self.mock_fs is False:
            return super(MockWikiParameters, self).fs_factory()
        return self.mock_fs or MockFileSystem(self.root, self.config)

    def index_factory(self):
        if self.mock_index is False:
            return super(MockWikiParameters, self).index_factory()
        return self.mock_index or MockWikiIndex()

    def db_factory(self):
        if self.mock_db is False:
            return super(MockWikiParameters, self).db_factory()
        return self.mock_db or MockDatabase()

    def scm_factory(self, for_init=False):
        if self.mock_scm is False:
            return super(MockWikiParameters, self).scm_factory(for_init)
        return self.mock_scm or MockSourceControl()

    def getFormatters(self):
        formatters = {
            passthrough_formatter: ['txt', 'html']
        }
        return formatters

    def getPageUpdater(self):
        return lambda wiki, url: wiki.update(url, cache_ext_data=True)

    def _loadConfig(self):
        default_config_path = os.path.join(
            os.path.dirname(__file__), '..',
            'wikked', 'resources', 'defaults.cfg')

        config = SafeConfigParser()
        config.readfp(open(default_config_path))
        config.set('wiki', 'root', '/fake/root')
        if self.config_text:
            with closing(io.StringIO(self.config_text)) as conf:
                config.readfp(conf)

        return config


def mock_os_walk(root_dir, root_node):
    queue = deque()
    queue.appendleft((root_dir, root_node))
    while len(queue) > 0:
        cur_dir, cur_node = queue.pop()

        dirnames = []
        filenames = []
        for name, child in cur_node.items():
            if isinstance(child, dict):
                dirnames.append(name)
            else:
                filenames.append(name)
        yield cur_dir, dirnames, filenames
        for name in dirnames:
            fullname = os.path.join(cur_dir, name)
            queue.appendleft((fullname, cur_node[name]))


class MockFileSystem(FileSystem):
    def __init__(self, root, config, structure=None):
        super(MockFileSystem, self).__init__(root, config)
        if not structure:
            self.structure = {}
        else:
            self.structure = MockFileSystem.flat_to_nested(structure)

    def getPageInfos(self, subdir=None):
        def tmp_walk(path):
            node = self._getNode(path)
            return mock_os_walk(path, node)

        orig_walk = os.walk
        os.walk = tmp_walk
        try:
            gen = super(MockFileSystem, self).getPageInfos(subdir)
            return list(gen)
        finally:
            os.walk = orig_walk

    def setPage(self, url, content):
        raise NotImplementedError()

    def _getPageInfo(self, path):
        pi = super(MockFileSystem, self)._getPageInfo(path)
        node = self._getNode(path)
        if node is not None:
            pi._content = node
        else:
            raise Exception("Can't find node: %s" % path)
        return pi

    def _getNode(self, path):
        node = self.structure
        path = path.lstrip('/')
        if path != '':
            for n in path.split('/'):
                if n not in node:
                    return None
                node = node[n]
        return node

    def _getPhysicalPath(self, url, is_file=True, make_new=False):
        def tmp_walk(path):
            node = self._getNode(path)
            return mock_os_walk(path, node)

        orig_walk = os.walk
        os.walk = tmp_walk
        try:
            return super(MockFileSystem, self)._getPhysicalPath(url, is_file,
                                                                make_new)
        finally:
            os.walk = orig_walk

    @staticmethod
    def flat_to_nested(flat):
        nested = {}
        for k, v in flat.items():
            bits = k.lstrip('/').split('/')
            cur = nested
            for i, b in enumerate(bits):
                if i < len(bits) - 1:
                    if b not in cur:
                        cur[b] = {}
                    cur = cur[b]
                else:
                    cur[b] = v
        return nested

    @staticmethod
    def save_structure(path, structure):
        if not os.path.isdir(path):
            os.makedirs(path)
        for node in structure:
            node_path = os.path.join(path, node)
            if isinstance(structure[node], str):
                with codecs.open(node_path, 'w', encoding='utf-8') as f:
                    f.write(structure[node])
            else:
                MockFileSystem.save_structure(node_path, structure[node])


class MockDatabase(Database):
    def __init__(self, content=None):
        super(MockDatabase, self).__init__()
        self.content = content

    def getPageUrls(self, subdir=None, uncached_only=False):
        return []

    def getPages(self, subdir=None, meta_query=None, uncached_only=False,
                 fields=None):
        return []

    def isCacheValid(self, page):
        return False

    def pageExists(self, url=None, path=None):
        return False

    def getLinksTo(self, url):
        return []

    def _getPageByUrl(self, url, fields):
        return None

    def _getPageByPath(self, path, fields):
        return None


class MockWikiIndex(WikiIndex):
    def __init__(self):
        super(MockWikiIndex, self).__init__()

    def search(self, query):
        # url, title, content_highlights
        return None


class MockSourceControl(SourceControl):
    def __init__(self):
        super(MockSourceControl, self).__init__()

    def getSpecialFilenames(self):
        return []

    def getHistory(self, path=None):
        return []

    def getState(self, path):
        raise NotImplementedError()

    def getRevision(self, path, rev):
        raise NotImplementedError()

    def diff(self, path, rev1, rev2):
        raise NotImplementedError()
