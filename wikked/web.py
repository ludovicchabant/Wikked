from flask import Flask, abort, g
from wiki import Wiki, WikiParameters

# Create the main app.
app = Flask("wikked")
app.config.from_object('wikked.settings')
app.config.from_envvar('WIKKED_SETTINGS', silent=True)


def create_wiki():
    params = WikiParameters(root=app.config.get('WIKI_ROOT'))
    params.logger = app.logger
    wiki = Wiki(params)
    wiki.start()
    return wiki

wiki = create_wiki()


# Set the wiki as a request global, and open/close the database.
@app.before_request
def before_request():
    if getattr(wiki, 'db', None):
        wiki.db.open()
    g.wiki = wiki


@app.teardown_request
def teardown_request(exception):
    if wiki is not None:
        if getattr(wiki, 'db', None):
            wiki.db.close()


# Make is serve static content in DEBUG mode.
if app.config['DEBUG']:
    from werkzeug import SharedDataMiddleware
    import os
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
      '/': os.path.join(os.path.dirname(__file__), 'static')
    })


# Customize logging.
if app.config.get('LOG_FORMAT'):
    import logging
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    app.logger.handlers = []
    app.logger.addHandler(handler)


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


# Import the views.
import views
