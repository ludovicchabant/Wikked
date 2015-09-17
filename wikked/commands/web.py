import os
import os.path
import imp
import logging
from wikked.commands.base import WikkedCommand, register_command


logger = logging.getLogger(__name__)


def autoreload_wiki_updater(wiki, url):
    wiki.db.uncachePages(except_url=url, only_required=True)


@register_command
class RunServerCommand(WikkedCommand):
    def __init__(self):
        super(RunServerCommand, self).__init__()
        self.name = 'runserver'
        self.description = ("Runs the wiki in a local web server.")

    def setupParser(self, parser):
        parser.add_argument('--host',
                help="The host to use",
                default='127.0.0.1')
        parser.add_argument('--port',
                help="The port to use",
                default=5000)
        parser.add_argument('--usetasks',
                help="Use background tasks for updating the wiki after a "
                     "page has been edited. You will have to run "
                     "`wk runtasks` at the same time as `wk runserver`.",
                action='store_true')
        parser.add_argument('-d', '--dev',
                help="Use development mode. "
                     "This makes Wikked use development assets (separate and "
                     "uncompressed scripts and stylesheets), along with using "
                     "code reloading and debugging.",
                action='store_true')
        parser.add_argument('--no-update',
                help="Don't auto-update the wiki if a page file has been "
                     "touched (which means you can refresh a locally modified "
                     "page with F5)",
                action='store_true')
        parser.add_argument('--no-startup-update',
                help="Don't update the wiki before starting the server.",
                action='store_true')
        parser.add_argument('-c', '--config',
                help="Pass some configuration value to the Flask application. "
                     "This must be of the form: name=value",
                nargs="*")

    def run(self, ctx):
        # Change working directory because the Flask app can currently
        # only initialize itself relative to that...
        # TODO: make the Flask initialization more clever.
        os.chdir(ctx.params.root)

        # Setup some settings that need to be set before the app is created.
        import wikked.settings
        if ctx.args.usetasks:
            wikked.settings.WIKI_ASYNC_UPDATE = True
        if ctx.args.config:
            for cv in ctx.args.config:
                cname, cval = cv.split('=')
                if cval in ['true', 'True', 'TRUE']:
                    setattr(wikked.settings, cname, True)
                else:
                    setattr(wikked.settings, cname, cval)

        # Remove Flask's default logging handler. Since the app is under the
        # overall Wikked package, logging is handled by the root logger
        # already.
        wikked.settings.WIKI_NO_FLASK_LOGGER = True

        # When running from the command line, we only have one web server
        # so make it also serve static files.
        wikked.settings.WIKI_SERVE_FILES = True
        if ctx.args.dev:
            wikked.settings.WIKI_DEV_ASSETS = True
        if not ctx.args.no_update:
            wikked.settings.WIKI_AUTO_RELOAD = True
            ctx.params.wiki_updater = autoreload_wiki_updater

        # Create/import the app.
        from wikked.web import app
        app.wiki_params = ctx.params
        ctx.wiki.db.hookupWebApp(app)

        # Update if needed.
        if (bool(app.config.get('WIKI_UPDATE_ON_START')) and
                not ctx.args.no_startup_update):
            ctx.wiki.updateAll()

        # Run!
        debug_mode = ctx.args.dev or app.config.get('DEBUG', False)
        app.run(
                host=ctx.args.host,
                port=ctx.args.port,
                debug=debug_mode,
                use_debugger=debug_mode,
                use_reloader=debug_mode)


@register_command
class RunTasksCommand(WikkedCommand):
    def __init__(self):
        super(RunTasksCommand, self).__init__()
        self.name = 'runtasks'
        self.description = "Runs the tasks to update the wiki in the background."

    def setupParser(self, parser):
        pass

    def run(self, ctx):
        # Import the Celery app and update its configuration with the same
        # stuff as what the Flask app got.
        from wikked.tasks import celery_app

        celery_app.conf.update(BROKER_URL='sqla+sqlite:///%(root)s/.wiki/broker.db')
        config_path = os.path.join(ctx.params.root, '.wiki', 'app.cfg')
        if os.path.isfile(config_path):
            obj = self._loadConfig(config_path)
            celery_app.conf.update(obj.__dict__)
        celery_app.conf.BROKER_URL = celery_app.conf.BROKER_URL % (
                { 'root': ctx.params.root })

        os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))
        argv = ['celery', 'worker', '-A', 'wikked.tasks']
        if ctx.args.debug:
            argv += ['-l', 'DEBUG']
        celery_app.start(argv)

    def _loadConfig(self, path):
        d = imp.new_module('config')
        d.__file__ = path
        try:
            with open(path) as config_file:
                exec(compile(config_file.read(), path, 'exec'), d.__dict__)
        except IOError as e:
            e.strerror = 'Unable to load Flask/Celery configuration file (%s)' % e.strerror
            raise
        return d
