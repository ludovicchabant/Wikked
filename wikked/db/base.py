

class Database(object):
    """ The base class for a database cache.
    """
    def __init__(self):
        pass

    def initDb(self, wiki):
        raise NotImplementedError()

    def open(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def reset(self, pages):
        raise NotImplementedError()

    def update(self, pages, force=False):
        raise NotImplementedError()

    def getPageUrls(self, subdir=None):
        raise NotImplementedError()

    def getPages(self, subdir=None, meta_query=None):
        raise NotImplementedError()

    def getPage(self, url=None, path=None):
        raise NotImplementedError()

    def pageExists(self, url=None, path=None):
        raise NotImplementedError()

    def getLinksTo(self, url):
        raise NotImplementedError()

