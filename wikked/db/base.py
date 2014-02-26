from wikked.utils import PageNotFoundError


class Database(object):
    """ The base class for a database cache.
    """
    def __init__(self):
        pass

    def start(self, wiki):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def reset(self, pages):
        raise NotImplementedError()

    def update(self, pages, force=False):
        raise NotImplementedError()

    def getPageUrls(self, subdir=None, uncached_only=False):
        raise NotImplementedError()

    def getPages(self, subdir=None, meta_query=None, uncached_only=False,
                 fields=None):
        raise NotImplementedError()

    def getPage(self, url=None, path=None, fields=None, raise_if_none=True):
        if not url and not path:
            raise ValueError("Either URL or path need to be specified.")
        if url and path:
            raise ValueError("Can't specify both URL and path.")
        if url:
            page = self._getPageByUrl(url, fields)
        elif path:
            page = self._getPageByPath(path, fields)
        else:
            raise NotImplementedError()
        if page is None and raise_if_none:
            raise PageNotFoundError(url or path)
        return page

    def cachePage(self, page):
        raise NotImplementedError()

    def pageExists(self, url=None, path=None):
        raise NotImplementedError()

    def getLinksTo(self, url):
        raise NotImplementedError()

    def _getPageByUrl(self, url, fields):
        raise NotImplementedError()

    def _getPageByPath(self, path, fields):
        raise NotImplementedError()
