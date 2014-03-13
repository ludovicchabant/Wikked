

class HitResult(object):
    def __init__(self, url, title, hl_text=None):
        self.url = url
        self.title = title
        self.hl_text = hl_text


class WikiIndex(object):
    def __init__(self):
        pass

    def start(self, wiki):
        pass

    def init(self, wiki):
        pass

    def postInit(self):
        pass

    def reset(self, pages):
        pass

    def update(self, pages):
        pass

    def search(self, query):
        raise NotImplementedError()

