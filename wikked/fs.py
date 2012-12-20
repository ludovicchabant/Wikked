import os
import os.path
import re
import string


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
    def __init__(self, root):
        self.root = root
        self.excluded = []

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
                rel_path = os.path.relpath(path, self.root)
                rel_path_split = os.path.splitext(rel_path)
                if rel_path_split[1] == '':
                    continue
                url = re.sub(r'[^A-Za-z0-9_\.\-\(\)/]+', '-', rel_path_split[0].lower())
                yield {
                        'url': url,
                        'path': path,
                        'name': rel_path_split[0],
                        'ext': rel_path_split[1]
                        }

    def getPage(self, url):
        path = self.getPhysicalPagePath(url)
        with open(path, 'r') as f:
            content = f.read()
        name = os.path.basename(path)
        name_split = os.path.splitext(name)
        return {
                'url': url,
                'path': path,
                'name': name_split[0],
                'ext': name_split[1],
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

    def getPhysicalPagePath(self, url):
        return self._getPhysicalPath(url, True)

    def _getPhysicalPath(self, url, is_file):
        if string.find(url, '..') >= 0:
            raise ValueError("Page URLs can't contain '..': " + url)

        # For each "part" in the given URL, find the first
        # file-system entry that would get slugified to an
        # equal string.
        current = self.root
        parts = url.lower().split('/')
        for i, part in enumerate(parts):
            names = os.listdir(current)
            for name in names:
                name_formatted = re.sub(r'[^A-Za-z0-9_\.\-\(\)]+', '-', name.lower())
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

