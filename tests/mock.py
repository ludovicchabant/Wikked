import re
import os.path
import types
import codecs
import logging
import StringIO
from wikked.page import Page
from wikked.fs import PageNotFoundError
from wikked.db import Database
from wikked.indexer import WikiIndex
from wikked.scm import SourceControl


class MockWikiParameters(object):
    def __init__(self):
        self.formatters = {
            self._passthrough: ['txt', 'html']
        }

        self.config_text = ""
        self.special_filenames = []
        self.use_db = False

        self.logger_factory = lambda: logging.getLogger('wikked.tests')
        self.page_factory = lambda wiki, url: MockPage(wiki, url)
        self.config_factory = lambda: StringIO.StringIO(self.config_text)
        self.fs_factory = lambda cfg: MockFileSystem()
        self.index_factory = lambda cfg: MockWikiIndex()
        self.db_factory = lambda cfg: MockDatabase()
        self.scm_factory = lambda cfg: MockSourceControl()

    def getSpecialFilenames(self):
        return self.special_filenames

    def _passthrough(self, text):
        return text


class MockPage(Page):
    def __init__(self, wiki, url):
        Page.__init__(self, wiki, url)


class MockDatabase(Database):
    def __init__(self, content=None, logger=None):
        Database.__init__(self, logger)
        self.content = content
        self.conn = None
        self._open_count = 0

    def initDb(self):
        pass

    def open(self):
        self._open_count += 1
        self.conn = 'MOCK_CONNECTION'

    def close(self):
        self._open_count -= 1
        if self._open_count < 0:
            raise Exception(
                "The database was closed more times than it was open.")
        elif self._open_count == 0:
            self.conn = None

    def reset(self, pages):
        pass

    def update(self, pages):
        pass

    def getPageUrls(self, subdir=None):
        return []

    def getPages(self, subdir=None):
        return []

    def getPage(self, url):
        return None

    def pageExists(self, url):
        return False

    def getLinksTo(self, url):
        return []


class MockFileSystem():
    def __init__(self, structure=None, slugify=Page.title_to_url, logger=None):
        if not structure:
            structure = []
        if not slugify:
            slugify = lambda x: x
        self.structure = structure
        self.slugify = slugify
        self.logger = logger
        self.excluded = []

    def getPageInfos(self, subdir=None):
        node = self._getNode(subdir)
        if node is None:
            raise PageNotFoundError()
        for n in self._getChildren(node):
            yield self._getPageInfo(n)

    def getPageInfo(self, path):
        node = self._getNode(path)
        if node is None:
            raise PageNotFoundError()
        return self._getPageInfo(node)

    def getPage(self, url):
        path = self._getPath(url, True)
        node = self._getNode(path)
        if node is None:
            raise PageNotFoundError()
        return self._getPageInfo(node, True)

    def setPage(self, path, content):
        raise NotImplementedError()

    def pageExists(self, url):
        try:
            self._getPath(url, True)
            return True
        except PageNotFoundError:
            return False

    def getPhysicalNamespacePath(self, url):
        raise NotImplementedError()

    def _getPageInfo(self, node, with_content=False):
        path_split = os.path.splitext(node['path'])
        url = self.slugify(path_split[0])
        info = {
            'url': url,
            'path': node['path']
            }
        if with_content:
            info['content'] = node['content']
        return info

    def _getNode(self, path):
        node = self.structure
        if path:
            for n in path.split('/'):
                if n not in node:
                    return None
                node = node[n]
        else:
            path = ''
        if isinstance(node, types.StringTypes):
            return {'type': 'file', 'path': path, 'content': node}
        return {'type': 'dir', 'path': path, 'content': node}

    def _getChildren(self, node):
        if node['type'] != 'dir':
            raise Exception("'%s' is not a directory." % node['path'])
        for name in node['content']:
            child_path = os.path.join(node['path'], name)
            child = node['content'][name]
            if isinstance(child, types.StringTypes):
                yield {
                    'type': 'file',
                    'path': child_path,
                    'content': child
                    }
            else:
                for c in self._getChildren({
                    'type': 'dir',
                    'path': child_path,
                    'content': child
                    }):
                    yield c

    def _getPath(self, url, is_file):
        path = ''
        current = self.structure
        parts = unicode(url).lower().split('/')
        for i, part in enumerate(parts):
            for name in current:
                name_slug = self.slugify(name)
                if is_file and i == len(parts) - 1:
                    if re.match(r"%s\.[a-z]+" % re.escape(part), name_slug):
                        current = current[name]
                        path = os.path.join(path, name)
                        break
                else:
                    if name_slug == part:
                        current = current[name]
                        path = os.path.join(path, name)
                        break
            else:
                # Failed to find a part of the URL.
                raise PageNotFoundError("No such page: " + url)
        return path

    @staticmethod
    def save_structure(path, structure):
        if not os.path.isdir(path):
            os.makedirs(path)
        for node in structure:
            node_path = os.path.join(path, node)
            if isinstance(structure[node], types.StringTypes):
                with codecs.open(node_path, 'w', encoding='utf-8') as f:
                    f.write(structure[node])
            else:
                MockFileSystem.save_structure(node_path, structure[node])


class MockWikiIndex(WikiIndex):
    def __init__(self, logger=None):
        WikiIndex.__init__(self, logger)

    def initIndex(self):
        pass

    def reset(self, pages):
        pass

    def update(self, pages):
        pass

    def search(self, query):
        # url, title, content_highlights
        return None


class MockSourceControl(SourceControl):
    def __init__(self, logger=None):
        SourceControl.__init__(self, logger)

    def initRepo(self):
        pass

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

    def commit(self, paths, op_meta):
        raise NotImplementedError()

    def revert(self, paths=None):
        raise NotImplementedError()
