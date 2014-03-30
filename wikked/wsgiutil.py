import os
import sys
import logging
import logging.handlers
from wikked.wiki import WikiParameters


def get_wsgi_app(wiki_root, log_file=None, async_update=True):
    os.chdir(wiki_root)
    logging.basicConfig(stream=sys.stderr)

    if async_update:
        import wikked.settings
        wikked.settings.WIKI_ASYNC_UPDATE = True

    from wikked.web import app
    app.set_wiki_params(WikiParameters(wiki_root))

    if log_file is not None:
        h = logging.handlers.RotatingFileHandler(log_file, maxBytes=4096)
        h.setLevel(logging.WARNING)
        app.logger.addHandler(h)

    return app

