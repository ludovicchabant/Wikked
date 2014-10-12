import os
import os.path
import logging
from flask import Flask, abort, g
from wikked.wiki import Wiki, WikiParameters


# Create the main app.
static_folder = os.path.join(os.path.dirname(__file__), 'static')
app = Flask(
        'wikked',
        static_folder=static_folder,
        static_url_path='/static')
app.config.from_object('wikked.settings')
app.config.from_envvar('WIKKED_SETTINGS', silent=True)


# Setup some config defaults.
app.config.setdefault('SQL_DEBUG', False)
app.config.setdefault('SQL_COMMIT_ON_TEARDOWN', False)
app.config.setdefault('WIKI_ROOT', None)
app.config.setdefault('WIKI_DEV_ASSETS', False)
app.config.setdefault('WIKI_UPDATE_ON_START', True)
app.config.setdefault('WIKI_AUTO_RELOAD', False)
app.config.setdefault('WIKI_ASYNC_UPDATE', False)
app.config.setdefault('WIKI_SERVE_FILES', False)
app.config.setdefault('WIKI_BROKER_URL', 'sqla+sqlite:///%(root)s/.wiki/broker.db')
app.config.setdefault('WIKI_NO_FLASK_LOGGER', False)
app.config.setdefault('PROFILE', False)
app.config.setdefault('PROFILE_DIR', None)


if app.config['WIKI_NO_FLASK_LOGGER']:
    app.logger.handlers = []


# Find the wiki root, and further configure the app if there's a
# config file in there.
wiki_root = app.config['WIKI_ROOT']
if wiki_root is None:
    from wikked.utils import find_wiki_root
    wiki_root = find_wiki_root()
if wiki_root is None:
    raise Exception("Can't find the wiki root to use.")
config_path = os.path.join(wiki_root, '.wiki', 'app.cfg')
if os.path.isfile(config_path):
    app.config.from_pyfile(config_path)


# Make the app serve static content and wiki assets in DEBUG mode.
if app.config['WIKI_DEV_ASSETS'] or app.config['WIKI_SERVE_FILES']:
    from werkzeug import SharedDataMiddleware
    import os
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/files': os.path.join(wiki_root, '_files')
    })


# Profiling
if app.config['PROFILE']:
    profile_dir = app.config['PROFILE_DIR']
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, profile_dir=profile_dir)


# Customize logging.
if app.config['DEBUG']:
    l = logging.getLogger('wikked')
    l.setLevel(logging.DEBUG)

if app.config['SQL_DEBUG']:
    l = logging.getLogger('sqlalchemy')
    l.setLevel(logging.DEBUG)

app.logger.debug("Creating Flask application...")


# This lets components further modify the wiki that's created for
# each request.
app.wikked_post_init = []


# We'll hook this up to the post-page-update event, where we want to
# clear all cached page lists.
def remove_page_lists(wiki, url):
    wiki.db.removeAllPageLists()


# When requested, set the wiki as a request global.
def get_wiki():
    wiki = getattr(g, '_wiki', None)
    if wiki is None:
        wiki = Wiki(app.wiki_params)
        for i in app.wikked_post_init:
            i(wiki)
        wiki.post_update_hooks.append(remove_page_lists)
        wiki.start()
        g.wiki = wiki
    return wiki


# Set the default wiki parameters.
app.wiki_params = WikiParameters(wiki_root)


# Login extension.
def user_loader(username):
    wiki = get_wiki()
    return wiki.auth.getUser(username)


from flask.ext.login import LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.user_loader(user_loader)
login_manager.unauthorized_handler(lambda: abort(401))


# Bcrypt extension.
from wikked.bcryptfallback import Bcrypt
app.bcrypt = Bcrypt(app)


# Import the views.
# (this creates a PyLint warning but it's OK)
# pylint: disable=unused-import
import wikked.views.error
import wikked.views.read
import wikked.views.edit
import wikked.views.history
import wikked.views.special
import wikked.views.admin


# Async wiki update.
if app.config['WIKI_ASYNC_UPDATE']:
    app.logger.debug("Will use Celery tasks to update the wiki...")
    from wikked.tasks import celery_app, update_wiki

    # Configure Celery.
    app.config['WIKI_BROKER_URL'] = app.config['WIKI_BROKER_URL'] % (
            {'root': wiki_root})
    celery_app.conf.update(app.config)
    app.logger.debug("Using Celery broker: %s" % app.config['WIKI_BROKER_URL'])

    # Make the wiki use the background update task.
    def async_updater(wiki):
        app.logger.debug("Running update task on Celery.")
        update_wiki.delay(wiki.root)
    app.wiki_params.wiki_updater = async_updater

