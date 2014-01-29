import os
import sys
import logging
import logging.handlers
from wikked.wiki import WikiParameters


def get_wsgi_app(wiki_root, log_file=None):
    os.chdir(wiki_root)
    logging.basicConfig(stream=sys.stderr)

    from wikked.web import app
    app.wiki_params = WikiParameters(wiki_root)

    if log_file is not None:
        h = logging.handlers.RotatingFileHandler(log_file, maxBytes=4096)
        h.setLevel(logging.WARNING)
        app.logger.addHandler(h)

    return app

