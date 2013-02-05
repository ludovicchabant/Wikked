import os
from flask import Flask, abort, g
from wiki import Wiki, WikiParameters

# Create the main app.
app = Flask("wikked")
app.config.from_object('wikked.settings')
app.config.from_envvar('WIKKED_SETTINGS', silent=True)


# Find the wiki root.
wiki_root = app.config.get('WIKI_ROOT')
if not wiki_root:
    wiki_root = os.getcwd()


# Make the app serve static content and wiki assets in DEBUG mode.
if app.config['DEBUG']:
    from werkzeug import SharedDataMiddleware
    import os
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
      '/': os.path.join(
          os.path.dirname(os.path.dirname(__file__)),
          'static'),
      '/files': os.path.join(wiki_root)
    })


# Customize logging.
if app.config.get('LOG_FORMAT'):
    import logging
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    app.logger.handlers = []
    app.logger.addHandler(handler)


# Set the wiki as a request global, and open/close the database.
# NOTE: this must happen before the login extension is registered
#       because it will also add a `before_request` callback, and
#       that will call our authentication handler that needs
#       access to the context instance for the wiki.
@app.before_request
def before_request():
    wiki.db.open()
    g.wiki = wiki


@app.teardown_request
def teardown_request(exception):
    wiki.db.close()


# Login extension.
def user_loader(username):
    return g.wiki.auth.getUser(username)

from flask.ext.login import LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.user_loader(user_loader)
login_manager.unauthorized_handler(lambda: abort(401))


# Bcrypt extension.
from flaskext.bcrypt import Bcrypt
app.bcrypt = Bcrypt(app)


# Create the wiki.
def create_wiki(update_on_start=True):
    params = WikiParameters(root=wiki_root)
    params.logger = app.logger
    wiki = Wiki(params)
    wiki.start(update_on_start)
    return wiki

wiki = create_wiki(bool(app.config.get('UPDATE_WIKI_ON_START')))


# Import the views.
import views

