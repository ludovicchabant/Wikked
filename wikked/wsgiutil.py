import logging
import wikked.settings


logger = logging.getLogger()


def get_wsgi_app(wiki_root=None, async_update=False, log_file=None,
        max_log_bytes=4096, log_backup_count=0, log_level=logging.INFO):
    if log_file:
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(log_file, maxBytes=max_log_bytes,
                                      backupCount=log_backup_count)
        handler.setLevel(log_level)
        logging.getLogger().addHandler(handler)

    logger.debug("Creating WSGI application.")
    if wiki_root:
        wikked.settings.WIKI_ROOT = wiki_root
    wikked.settings.WIKI_ASYNC_UPDATE = async_update
    from wikked.web import app
    return app

