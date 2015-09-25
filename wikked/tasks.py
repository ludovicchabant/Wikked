import logging
from wikked.wiki import Wiki, WikiParameters, BACKGROUND_CONTEXT


logger = logging.getLogger(__name__)


try:
    from celery import Celery
except ImportError:
    logger.error("Celery is needed to run background tasks.")
    logger.error("Install it with: pip install celery")
    raise


logger.debug("Creating Celery application...")
celery_app = Celery('wikked', include=['wikked.tasks'])


class wiki_session(object):
    def __init__(self, wiki_root):
        self.wiki_root = wiki_root
        self.wiki = None

    def __enter__(self):
        params = WikiParameters(self.wiki_root, ctx=BACKGROUND_CONTEXT)
        self.wiki = Wiki(params)
        self.wiki.start(False)
        return self.wiki

    def __exit__(self, type, value, traceback):
        if self.wiki.db.session:
            self.wiki.db.session.remove()
        return False


@celery_app.task
def update_wiki(wiki_root):
    with wiki_session(wiki_root) as wiki:
        wiki.updateAll()

