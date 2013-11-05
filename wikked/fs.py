import os
import os.path
import re
import string
import codecs
import logging
from utils import title_to_url


class PageNotFoundError(Exception):
    """ An error raised when no physical file
       is found for a given URL.
    """
    pass


class PageInfo(object):
    def __init__(self, url, path):
        self.url = url
        self.path = path
        self._content = None

    @property
    def content(self):
        if self._content is None:
            with codecs.open(self.path, 'r', encoding='utf-8') as f:
                self._content = f.read()
        return self._content


class FileSystem(object):
    """ A class responsible for mapping page URLs to
        file-system paths, and for scanning the file-system
        to list existing pages.
    """
    def __init__(self, root, logger=None):
        self.root = unicode(root)

        if logger is None:
            logger = logging.getLogger('wikked.fs')
        self.logger = logger

        self.excluded = []
        self.page_extensions = None

    def getPageInfos(self, subdir=None):
        basepath = self.root
        if subdir is not None:
            basepath = self.getPhysicalNamespacePath(subdir)

        for dirpath, dirnames, filenames in os.walk(basepath):
            dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) not in self.excluded]
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if path in self.excluded:
                    continue
                page_info = self.getPageInfo(path)
                if page_info is not None:
                    yield page_info

    def getPageInfo(self, path):
        if not isinstance(path, unicode):
            path = unicode(path)
        for e in self.excluded:
            if path.startswith(e):
                return None
        return self._getPageInfo(path)

    def getPage(self, url):
        path = self.getPhysicalPagePath(url)
        return PageInfo(url, path)

    def setPage(self, url, content):
        path = self.getPhysicalPagePath(url)
        with codecs.open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return PageInfo(url, path)

    def pageExists(self, url):
        try:
            self.getPhysicalPagePath(url)
            return True
        except PageNotFoundError:
            return False

    def getPhysicalPagePath(self, url):
        return self._getPhysicalPath(url, True)

    def getPhysicalNamespacePath(self, url):
        return self._getPhysicalPath(url, False)

    def _getPageInfo(self, path):
        rel_path = os.path.relpath(path, self.root)
        rel_path_split = os.path.splitext(rel_path)
        ext = rel_path_split[1].lstrip('.')
        name = rel_path_split[0]
        if len(ext) == 0:
            return None
        if self.page_extensions is not None and ext not in self.page_extensions:
            return None

        url = ''
        parts = unicode(name).lower().split(os.sep)
        for i, part in enumerate(parts):
            if i > 0:
                url += '/'
            url += title_to_url(part)
        return PageInfo(url, path)

    def _getPhysicalPath(self, url, is_file):
        if string.find(url, '..') >= 0:
            raise ValueError("Page URLs can't contain '..': " + url)

        # For each "part" in the given URL, find the first
        # file-system entry that would get slugified to an
        # equal string.
        current = self.root
        parts = unicode(url).lower().split('/')
        for i, part in enumerate(parts):
            names = os.listdir(current)
            for name in names:
                name_formatted = title_to_url(name)
                if is_file and i == len(parts) - 1:
                    # If we're looking for a file and this is the last part,
                    # look for something similar but with an extension.
                    if re.match(r"%s\.[a-z]+" % re.escape(part), name_formatted):
                        current = os.path.join(current, name)
                        break
                else:
                    if name_formatted == part:
                        current = os.path.join(current, name)
                        break
            else:
                # Failed to find a part of the URL.
                raise PageNotFoundError("No such page: " + url)
        return current
