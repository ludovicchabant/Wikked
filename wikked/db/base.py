from wikked.utils import PageNotFoundError


class PageListNotFound(Exception):
    def __init__(self, list_name):
        super(PageListNotFound, self).__init__("No such page list: %s" % list_name)


class Database(object):
    """ The base class for a database cache.
    """
    def start(self, wiki):
        """ Called when the wiki is started. """
        pass

    def init(self, wiki):
        """ Called when a new wiki is created. """
        pass

    def postInit(self):
        """ Called after a new wiki has been created. """
        pass

    def close(self, exception):
        """ Called when the wiki is disposed of. """
        pass

    def reset(self, page_infos):
        """ Called when the DB cache should be re-build from scratch
            based on the given page infos. """
        pass

    def updatePage(self, page_info):
        """ Update the given page's cache info based on the given page
            info. """
        pass

    def updateAll(self, page_infos, force=False):
        """ Update all the pages in the wiki based on the given pages
            infos. """
        pass

    def getPageUrls(self, subdir=None, uncached_only=False):
        """ Return page URLs. """
        raise NotImplementedError()

    def getPages(self, subdir=None, meta_query=None, uncached_only=False,
                 endpoint_only=None, no_endpoint_only=False, fields=None):
        """ Return pages from the DB cache. """
        raise NotImplementedError()

    def getPage(self, url=None, path=None, fields=None, raise_if_none=True):
        """ Gets a page from the DB cache. """
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
        """ Cache resolved information from the given page. """
        pass

    def uncachePages(self, except_url=None, only_required=False):
        """ Invalidates resolved information for pages in the wiki. """
        pass

    def pageExists(self, url=None, path=None):
        """ Returns whether a given page exists. """
        raise NotImplementedError()

    def getLinksTo(self, url):
        """ Gets the list of links to a given page. """
        raise NotImplementedError()

    def _getPageByUrl(self, url, fields):
        raise NotImplementedError()

    def _getPageByPath(self, path, fields):
        raise NotImplementedError()

    def addPageList(self, list_name, pages):
        pass

    def getPageList(self, list_name, fields=None, valid_only=True):
        raise PageListNotFound(list_name)

    def getPageListOrNone(self, list_name, fields=None, valid_only=True):
        try:
            return list(self.getPageList(list_name, fields, valid_only))
        except PageListNotFound:
            return None

    def removePageList(self, list_name):
        pass

    def removeAllPageLists(self):
        pass

