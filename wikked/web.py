import os
import os.path
import logging
import urllib.parse
from werkzeug import SharedDataMiddleware
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
app.config.setdefault('WIKI_BROKER_URL',
                      'sqla+sqlite:///%(root)s/.wiki/broker.db')
app.config.setdefault('WIKI_NO_FLASK_LOGGER', False)
app.config.setdefault('PROFILE', False)
app.config.setdefault('PROFILE_DIR', None)
app.config.setdefault('INFLUXDB_HOST', None)
app.config.setdefault('INFLUXDB_PORT', 8086)
app.config.setdefault('INFLUXDB_USERNAME', 'root')
app.config.setdefault('INFLUXDB_PASSWORD', 'root')
app.config.setdefault('INFLUXDB_DATABASE', 'database')


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
    app.wsgi_app = SharedDataMiddleware(
            app.wsgi_app,
            {'/files': os.path.join(wiki_root, '_files')})


# In DEBUG mode, also serve raw assets instead of static ones.
if app.config['WIKI_DEV_ASSETS']:
    assets_folder = os.path.join(os.path.dirname(__file__), 'assets')
    app.wsgi_app = SharedDataMiddleware(
            app.wsgi_app,
            {'/dev-assets': assets_folder},
            cache=False)  # Etag/caching seems broken


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


# When requested, set the wiki as a request global.
def get_wiki():
    wiki = getattr(g, '_wiki', None)
    if wiki is None:
        wiki = Wiki(app.wiki_params)
        for i in app.wikked_post_init:
            i(wiki)
        wiki.start()
        g.wiki = wiki
    return wiki


# Set the default wiki parameters.
app.wiki_params = WikiParameters(wiki_root)


# Login extension.
def user_loader(username):
    wiki = get_wiki()
    return wiki.auth.getUser(username)


# Setup the Jinja environment.
def get_read_url(url):
    return '/read/' + url.lstrip('/')


def get_edit_url(url):
    return '/edit/' + url.lstrip('/')


def get_rev_url(url, rev):
    return '/rev/%s?%s' % (url.lstrip('/'),
                           urllib.parse.urlencode({'rev': rev}))


def get_diff_url(url, rev1=None, rev2=None):
    args = {}
    if rev1 is not None:
        args['rev1'] = rev1
    if rev2 is not None:
        args['rev2'] = rev2
    if len(args) > 0:
        return '/diff/%s?%s' % (url.lstrip('/'),
                                urllib.parse.urlencode(args))
    return '/diff/%s' % url.lstrip('/')


app.jinja_env.globals.update({
    'get_read_url': get_read_url,
    'get_edit_url': get_edit_url,
    'get_rev_url': get_rev_url,
    'get_diff_url': get_diff_url
    })


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
import wikked.api.admin
import wikked.api.edit
import wikked.api.history
import wikked.api.read
import wikked.api.special
import wikked.views.admin
import wikked.views.edit
import wikked.views.error
import wikked.views.history
import wikked.views.read
import wikked.views.special


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


# InfluxDB metrics.
if app.config['INFLUXDB_HOST']:
    try:
        import influxdb
    except ImportError:
        raise Exception("Please install the `influxdb` package if you need "
                        "analytics for your Wikked app.")
    host = app.config['INFLUXDB_HOST']
    port = app.config['INFLUXDB_PORT']
    username = app.config['INFLUXDB_USERNAME']
    password = app.config['INFLUXDB_PASSWORD']
    database = app.config['INFLUXDB_DATABASE']
    metrics_db = influxdb.InfluxDBClient(host, port, username, password, database)
    app.logger.info("Opening InfluxDB %s on %s:%s as %s." % (
        database, host, port, username))

    import time
    from flask import g, request, request_started, request_tearing_down
    def on_request_started(sender, **extra):
        g.metrics_start_time = time.clock()
    def on_request_tearing_down(sender, **extra):
        duration = time.clock() - g.metrics_start_time
        data = [
                  {
                      "name": "requests",
                      "columns": ["request_path", "compute_time"],
                      "points": [
                          [str(request.path), duration]
                          ]
                      }
                  ]
        metrics_db.write_points(data)

    request_started.connect(on_request_started, app)
    request_tearing_down.connect(on_request_tearing_down, app)

