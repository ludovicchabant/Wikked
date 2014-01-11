import os
import os.path
import logging
from flask import Flask, abort, g
from utils import find_wiki_root

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
app.config.setdefault('UPDATE_WIKI_ON_START', True)
app.config.setdefault('SYNCHRONOUS_UPDATE', True)


# Find the wiki root, and further configure the app if there's a
# config file in there.
wiki_root = app.config['WIKI_ROOT']
if wiki_root is None:
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
    g.wiki = wiki


@app.teardown_request
def teardown_request(exception):
    return exception


# SQLAlchemy.
@app.teardown_appcontext
def shutdown_session(exception=None):
    wiki = getattr(g, 'wiki', None)
    if wiki:
        if app.config['SQL_COMMIT_ON_TEARDOWN'] and exception is None:
            wiki.db.session.commit()
        wiki.db.session.remove()
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
try:
    from flaskext.bcrypt import Bcrypt
    app.bcrypt = Bcrypt(app)
except ImportError:
    app.logger.warning("Bcrypt not available... falling back to SHA512.")

    import hashlib

    class SHA512Fallback(object):
        def check_password_hash(self, reference, check):
            check_hash = hashlib.sha512(check).hexdigest()
            return check_hash == reference

        def generate_password_hash(self, password):
            return hashlib.sha512(password).hexdigest()

    app.bcrypt = SHA512Fallback()


# Create the wiki.
from wiki import Wiki, WikiParameters

def create_wiki(update_on_start=True):
    params = WikiParameters(root=wiki_root)
    wiki = Wiki(params)
    wiki.start(update_on_start)
    return wiki


wiki = create_wiki(bool(app.config.get('UPDATE_WIKI_ON_START')))


# Import the views.
# (this creates a PyLint warning but it's OK)
# pylint: disable=unused-import
import views.error
import views.read
import views.edit
import views.history
import views.special
import views.admin

