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
        parser.add_argument('--production',
                help="Don't enable the debugger or reloader",
                action='store_true')

    def run(self, ctx):
        # Change working directory because the Flask app can currently
        # only initialize itself relative to that...
        # TODO: make the Flask initialization more clever.
        os.chdir(ctx.params.root)

        from wikked.web import app
        app.wiki_params = ctx.params

        if bool(app.config.get('UPDATE_WIKI_ON_START')):
            ctx.wiki.update()

        use_dbg_and_rl = not ctx.args.production

        if ctx.args.debug:
            app.config['DEBUG'] = True

        app.run(
                host=ctx.args.host,
                port=ctx.args.port,
                debug=app.config.get('DEBUG', True),
                use_debugger=use_dbg_and_rl,
                use_reloader=use_dbg_and_rl)

