

class HitResult(object):
    def __init__(self, url, title, hl_text=None):
        self.url = url
        self.title = title
        self.hl_text = hl_text


class WikiIndex(object):
    """ The search index for the wiki, allowing the user to run queries
        to find pages.
    """
    def start(self, wiki):
        """ Called when the wiki is started. """
        pass

    def init(self, wiki):
        """ Called when a new wiki is created. """
        pass

    def postInit(self):
        """ Called after a new wiki was created. """
        pass

    def reset(self, pages):
        """ Called when the index should be re-created from scratch
            based on the given pages. """
        pass

    def updatePage(self, page):
        """ Called when the entry for the given page should be updated
            with the latest information. """
        pass

    def updateAll(self, pages):
        """ Called when the entries for the given pages should be
            updated with the latest information. """
        pass

    def search(self, query):
        raise NotImplementedError()

