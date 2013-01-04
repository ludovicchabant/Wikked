from flask import Flask, abort

# Create the main app.
app = Flask(__name__)
app.config.from_object('wikked.settings')
app.config.from_envvar('WIKKED_SETTINGS', silent=True)

if app.config['DEBUG']:
    from werkzeug import SharedDataMiddleware
    import os
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
      '/': os.path.join(os.path.dirname(__file__), 'static')
    })

# The main Wiki instance.
from wiki import Wiki
wiki = Wiki(root=app.config.get('WIKI_ROOT'), logger=app.logger)

# Import views and user loader.
import wikked.views

# Login extension.
from flask.ext.login import LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.user_loader(wiki.auth.getUser)
login_manager.unauthorized_handler(lambda: abort(401))

# Bcrypt extension.
from flaskext.bcrypt import Bcrypt
app.bcrypt = Bcrypt(app)

