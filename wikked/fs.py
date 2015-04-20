import os
import os.path
import re
import codecs
import fnmatch
import logging
import itertools
from .utils import (PageNotFoundError, NamespaceNotFoundError,
        split_page_url)


META_ENDPOINT = '_meta'


logger = logging.getLogger(__name__)


valid_filename_pattern = re.compile('^[\w \.\-\(\)\[\]\\/]+$', re.UNICODE)


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
    def __init__(self, root, config):
        self.root = root

        self.excluded = None
        self.page_extensions = None
        self.default_extension = config.get('wiki', 'default_extension')

    def start(self, wiki):
        self.page_extensions = list(set(
            itertools.chain(*wiki.formatters.values())))

        excluded = []
        excluded += wiki.getSpecialFilenames()
        excluded += wiki.scm.getSpecialFilenames()
        self.excluded = [os.path.join(self.root, e) for e in excluded]

    def init(self, wiki):
        pass

    def postInit(self):
        pass

    def getPageInfos(self, subdir=None):
        basepath = self.root
        if subdir is not None:
            basepath = self.getPhysicalNamespacePath(subdir)

        logger.debug("Scanning for pages in: %s" % basepath)
        for dirpath, dirnames, filenames in os.walk(basepath):
            incl_dirnames = []
            for d in dirnames:
                full_d = os.path.join(dirpath, d)
                for e in self.excluded:
                    if fnmatch.fnmatch(full_d, e):
                        break
                else:
                    incl_dirnames.append(d)
            dirnames[:] = incl_dirnames
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                page_info = self.getPageInfo(path)
                if page_info is not None:
                    yield page_info

    def getPageInfo(self, path):
        logger.debug("Reading page info from: %s" % path)
        for e in self.excluded:
            if fnmatch.fnmatch(path, e):
                return None
        return self._getPageInfo(path)

    def findPageInfo(self, url):
        logger.debug("Searching for page: %s" % url)
        path = self.getPhysicalPagePath(url)
        return PageInfo(url, path)

    def setPage(self, url, content):
        path = self.getPhysicalPagePath(url, make_new=True)
        logger.debug("Saving page '%s' to: %s" % (url, path))
        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname, 0o775)
        with codecs.open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return PageInfo(url, path)

    def pageExists(self, url):
        logger.debug("Searching for page: %s" % url)
        try:
            self.getPhysicalPagePath(url)
            return True
        except PageNotFoundError:
            return False

    def getPhysicalPagePath(self, url, make_new=False):
        return self._getPhysicalPath(url, is_file=True, make_new=make_new)

    def getPhysicalNamespacePath(self, url, make_new=False):
        return self._getPhysicalPath(url, is_file=False, make_new=make_new)

    def _getPageInfo(self, path):
        meta = None
        abs_path = os.path.abspath(path)
        rel_path = os.path.relpath(path, self.root)
        if rel_path.startswith(META_ENDPOINT + os.sep):
            rel_path = rel_path[len(META_ENDPOINT) + 1:]
            meta, rel_path = rel_path.split(os.sep, 1)
        rel_path_split = os.path.splitext(rel_path)
        ext = rel_path_split[1].lstrip('.')
        name = rel_path_split[0].replace(os.sep, '/')
        if len(ext) == 0:
            return None
        if self.page_extensions is not None and ext not in self.page_extensions:
            return None

        url = '/' + name
        if meta:
            url = "%s:/%s" % (meta.lower(), name)
        return PageInfo(url, abs_path)

    def _getPhysicalPath(self, url, is_file=True, make_new=False):
        endpoint, url = split_page_url(url)
        if url[0] != '/':
            raise ValueError("Page URLs need to be absolute: " + url)
        if '..' in url:
            raise ValueError("Page URLs can't contain '..': " + url)

        # Find the root directory in which we'll be searching for the
        # page file.
        root = self.root
        if endpoint:
            root = os.path.join(self.root, META_ENDPOINT, endpoint)

        # Make the URL into a relative file-system path.
        url_path = url[1:].replace('/', os.sep)
        if url_path[0] == os.sep:
            raise ValueError("Page URLs can only have one slash at the "
                    "beginning. Got: %s" % url)

        # If we want a non-existing file's path, just build that.
        if make_new:
            if (url_path[-1] == os.sep or
                    not valid_filename_pattern.match(url_path)):
                raise ValueError("Invalid URL: %s" % url_path)
            return os.path.join(root, url_path + '.' + self.default_extension)

        # Find the right file-system entry for this URL.
        url_path = os.path.join(root, url_path)
        if is_file:
            dirname, basename = os.path.split(url_path)
            if basename == '':
                raise ValueError("Invalid URL: %s" % url_path)
            if not os.path.isdir(dirname):
                self._throwNotFoundError(url, root, is_file)

            it = os.walk(dirname)
            # TODO: This is weird, `itertools.islice` seems useless here.
            for _, __, ___ in it:
                filenames = ___
                break
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if name == basename:
                    return os.path.join(dirname, filename)
            self._throwNotFoundError(url, root, is_file)
        else:
            if os.path.isdir(url_path):
                return url_path
            self._throwNotFoundError(url, root, is_file)

    def _throwNotFoundError(self, url, searched, is_file):
        if is_file:
            raise PageNotFoundError("No such page '%s' in: %s" % (url, searched))
        else:
            raise NamespaceNotFoundError("No such namespace '%s' in: %s" % (url, searched))

