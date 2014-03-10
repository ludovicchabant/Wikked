import os
import logging
from wikked.commands.base import WikkedCommand, register_command


logger = logging.getLogger(__name__)


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
        parser.add_argument('-d', '--dev',
                help="Use development mode. "
                     "This makes Wikked use development assets (separate and "
                     "uncompressed scripts and stylesheets), along with using "
                     "code reloading and debugging.",
                action='store_true')

    def run(self, ctx):
        # Change working directory because the Flask app can currently
        # only initialize itself relative to that...
        # TODO: make the Flask initialization more clever.
        os.chdir(ctx.params.root)

        from wikked.web import app

        # Setup the app.
        if ctx.args.dev:
            app.config['DEV_ASSETS'] = True
        app.config['WIKI_AUTO_RELOAD'] = True

        app.wiki_params = ctx.params
        if bool(app.config.get('UPDATE_WIKI_ON_START')):
            ctx.wiki.update()

        # Run!
        debug_mode = ctx.args.dev or app.config.get('DEBUG', False)
        app.run(
                host=ctx.args.host,
                port=ctx.args.port,
                debug=debug_mode,
                use_debugger=debug_mode,
                use_reloader=debug_mode)

