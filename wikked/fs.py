import os
import os.path
import re
import string
import codecs


class PageNotFoundError(Exception):
    """ An error raised when no physical file
       is found for a given URL.
    """
    pass


class FileSystem(object):
    """ A class responsible for mapping page URLs to
        file-system paths, and for scanning the file-system
        to list existing pages.
    """
    def __init__(self, root, slugify=None):
        self.root = unicode(root)
        self.slugify = slugify
        self.excluded = []
        self.page_extensions = None

        if slugify is None:
            self.slugify = lambda x: x

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
        with codecs.open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        name = os.path.basename(path)
        name_split = os.path.splitext(name)
        return {
                'url': url,
                'path': path,
                'name': name_split[0],
                'ext': name_split[1].lstrip('.'),
                'content': content
                }

    def pageExists(self, url):
        try:
            self.getPhysicalPagePath(url)
            return True
        except PageNotFoundError:
            return False

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
        url = self.slugify(name)
        return {
                'url': url,
                'path': path,
                'name': name,
                'ext': ext
                }

    def getPhysicalPagePath(self, url):
        return self._getPhysicalPath(url, True)

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
                name_formatted = self.slugify(name)
                if is_file and i == len(parts) - 1:
                    # If we're looking for a file and this is the last part,
                    # look for something similar but with an extension.
                    if re.match("%s\.[a-z]+" % re.escape(part), name_formatted):
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

