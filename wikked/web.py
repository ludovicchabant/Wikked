import os
import os.path
import logging
from flask import Flask, abort, g
from wikked.wiki import Wiki


# Create the main app.
static_folder = os.path.join(os.path.dirname(__file__), 'static')
app = Flask(
        'wikked',
        static_folder=static_folder,
        static_url_path='/static')
app.config.from_object('wikked.settings')
app.config.from_envvar('WIKKED_SETTINGS', silent=True)


# Setup some config defaults.
app.config.setdefault('DEV_ASSETS', False)
app.config.setdefault('SQL_DEBUG', False)
app.config.setdefault('SQL_COMMIT_ON_TEARDOWN', False)
app.config.setdefault('WIKI_ROOT', None)
app.config.setdefault('UPDATE_WIKI_ON_START', True)
app.config.setdefault('WIKI_AUTO_RELOAD', False)
app.config.setdefault('SYNCHRONOUS_UPDATE', True)


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
if app.config['DEBUG']:
    from werkzeug import SharedDataMiddleware
    import os
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/files': os.path.join(wiki_root, '_files')
    })


# Customize logging.
if app.config['DEBUG']:
    l = logging.getLogger('wikked')
    l.setLevel(logging.DEBUG)

if app.config['SQL_DEBUG']:
    l = logging.getLogger('sqlalchemy')
    l.setLevel(logging.DEBUG)


# Set the wiki as a request global, and open/close the database.
# NOTE: this must happen before the login extension is registered
#       because it will also add a `before_request` callback, and
#       that will call our authentication handler that needs
#       access to the context instance for the wiki.
@app.before_request
def before_request():
    wiki = Wiki(app.wiki_params)
    wiki.start()
    g.wiki = wiki


@app.teardown_request
def teardown_request(exception):
    return exception


# SQLAlchemy.
# TODO: this totally assumes things about the wiki's DB API.
@app.teardown_appcontext
def shutdown_session(exception=None):
    wiki = getattr(g, 'wiki', None)
    if wiki:
        wiki.db.close(
                commit=app.config['SQL_COMMIT_ON_TEARDOWN'],
                exception=exception)
    return exception


# Login extension.
def user_loader(username):
    return g.wiki.auth.getUser(username)


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

