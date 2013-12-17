

class HitResult(object):
    def __init__(self, url, title, hl_text=None):
        self.url = url
        self.title = title
        self.hl_text = hl_text


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

