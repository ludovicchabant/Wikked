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
app.config.setdefault('WIKI_UPDATE_ON_START', True)
app.config.setdefault('WIKI_AUTO_RELOAD', False)
app.config.setdefault('WIKI_ASYNC_UPDATE', False)
app.config.setdefault('WIKI_SERVE_FILES', False)
app.config.setdefault('WIKI_BROKER_URL',
                      'sqla+sqlite:///%(root)s/.wiki/broker.db')
app.config.setdefault('WIKI_NO_FLASK_LOGGER', False)
app.config.setdefault('WIKI_STYLESHEET', None)
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
app.config['WIKI_ROOT'] = wiki_root
app.config['WIKI_FILES_DIR'] = os.path.join(wiki_root, '_files')
if app.config['WIKI_SERVE_FILES']:
    app.wsgi_app = SharedDataMiddleware(
            app.wsgi_app,
            {'/files': app.config['WIKI_FILES_DIR']})


# Add a special route for the `.well-known` directory.
app.wsgi_app = SharedDataMiddleware(
        app.wsgi_app,
        {'/.well-known': os.path.join(wiki_root, '.well-known')})


# Profiling
if app.config['PROFILE']:
    profile_dir = app.config['PROFILE_DIR']
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, profile_dir=profile_dir)


# Customize logging.
if app.config['DEBUG']:
    lg = logging.getLogger('wikked')
    lg.setLevel(logging.DEBUG)

if app.config['SQL_DEBUG']:
    lg = logging.getLogger('sqlalchemy')
    lg.setLevel(logging.DEBUG)

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
app.wiki_params = app.config.get('WIKI_FACTORY_PARAMETERS', None)
if app.wiki_params is None:
    app.wiki_params = WikiParameters(wiki_root)


# Just uncache pages when the user has edited one.
def uncaching_wiki_updater(wiki, url):
    app.logger.debug("Uncaching all pages because %s was edited." % url)
    wiki.db.uncachePages(except_url=url, only_required=True)


app.wiki_params.wiki_updater = uncaching_wiki_updater


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


from flask_login import LoginManager  # NOQA
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.user_loader(user_loader)
login_manager.unauthorized_handler(lambda: abort(401))


# Bcrypt extension.
from wikked.bcryptfallback import Bcrypt  # NOQA
app.bcrypt = Bcrypt(app)


# Import the views.
import wikked.commonroutes    # NOQA
import wikked.api.admin       # NOQA
import wikked.api.edit        # NOQA
import wikked.api.history     # NOQA
import wikked.api.read        # NOQA
import wikked.api.special     # NOQA
import wikked.api.user        # NOQA
import wikked.views.admin     # NOQA
import wikked.views.edit      # NOQA
import wikked.views.error     # NOQA
import wikked.views.history   # NOQA
import wikked.views.read      # NOQA
import wikked.views.special   # NOQA
import wikked.views.user      # NOQA


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
    metrics_db = influxdb.InfluxDBClient(host, port, username, password,
                                         database)
    app.logger.info("Opening InfluxDB %s on %s:%s as %s." % (
        database, host, port, username))

    import time
    from flask import request, request_started, request_tearing_down

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
