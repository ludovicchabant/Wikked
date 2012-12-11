from flask import Flask

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

# Login extension.
from flask.ext.login import LoginManager
login_manager = LoginManager()
login_manager.setup_app(app)

# The main Wiki instance.
from wiki import Wiki
wiki = Wiki(logger=app.logger)

# Import views and user loader.
import wikked.views
import wikked.auth

