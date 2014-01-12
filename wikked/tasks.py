import logging
from celery import Celery
from wiki import Wiki, WikiParameters


logger = logging.getLogger(__name__)


#TODO: Make those settings configurable!
app = Celery(
        'wikked',
        broker='amqp://',
        backend='amqp://',
        include=['wikked.tasks'])


class wiki_session(object):
    def __init__(self, wiki_root):
        self.wiki_root = wiki_root
        self.wiki = None

    def __enter__(self):
        params = WikiParameters(root=self.wiki_root)
        self.wiki = Wiki(params)
        self.wiki.start(False)
        return self.wiki

    def __exit__(self, type, value, traceback):
        if self.wiki.db.session:
            self.wiki.db.session.remove()
        return False


@app.task
def update_wiki(wiki_root):
    with wiki_session(wiki_root) as wiki:
        wiki.update()

