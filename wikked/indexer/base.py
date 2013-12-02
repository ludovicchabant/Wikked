

class WikiIndex(object):
    def __init__(self):
        pass

    def initIndex(self, wiki):
        raise NotImplementedError()

    def reset(self, pages):
        raise NotImplementedError()

    def update(self, pages):
        raise NotImplementedError()

    def search(self, query):
        raise NotImplementedError()

