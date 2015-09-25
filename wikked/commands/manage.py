import os
import os.path
import shutil
import logging
from wikked.commands.base import WikkedCommand, register_command
from wikked.wiki import INIT_CONTEXT


logger = logging.getLogger(__name__)


@register_command
class InitCommand(WikkedCommand):
    def __init__(self):
        super(InitCommand, self).__init__()
        self.name = 'init'
        self.description = "Creates a new wiki"
        self.requires_wiki = False

    def setupParser(self, parser):
        parser.add_argument(
                'destination',
                help="The destination directory to create the wiki")
        parser.add_argument(
                '--hg',
                help="Use Mercurial as a revision system (default)",
                action='store_true')
        parser.add_argument(
                '--git',
                help="Use Git as a revision system",
                action='store_true')
        parser.add_argument(
                '--bare',
                help="Don't create the default pages",
                action='store_true')

    def run(self, ctx):
        if ctx.args.git:
            raise Exception("Git is not yet fully supported.")

        path = ctx.args.destination or os.getcwd()
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            os.makedirs(path)

        logger.info("Initializing new wiki at: %s" % path)
        from wikked.wiki import WikiParameters, Wiki
        parameters = WikiParameters(path, ctx=INIT_CONTEXT)
        wiki = Wiki(parameters)
        wiki.init()

        if not ctx.args.bare:
            src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'resources', 'init')

            shutil.copy(os.path.join(src_dir, 'Main page.md'), path)
            shutil.copy(os.path.join(src_dir, 'Sandbox.md'), path)
            wiki.scm.commit(
                [os.path.join(path, 'Main page.md'),
                 os.path.join(path, 'Sandbox.md')],
                {'message': "Initial commit"})


@register_command
class ResetCommand(WikkedCommand):
    def __init__(self):
        super(ResetCommand, self).__init__()
        self.name = 'reset'
        self.description = ("Re-generates the database and the full-text "
                            "search index.")

    def setupParser(self, parser):
        parser.add_argument(
                '--single-threaded',
                help="Run in single-threaded mode",
                action='store_true')
        parser.add_argument(
                '--index-only',
                help="Only reset the full-text search index",
                action='store_true')

    def run(self, ctx):
        parallel = not ctx.args.single_threaded
        if ctx.args.index_only:
            ctx.wiki.index.reset(ctx.wiki.getPages())
        else:
            ctx.wiki.reset(parallel=parallel)


@register_command
class UpdateCommand(WikkedCommand):
    def __init__(self):
        super(UpdateCommand, self).__init__()
        self.name = 'update'
        self.description = (
                "Updates the database and the full-text-search "
                "index with any changed/new files.")

    def setupParser(self, parser):
        parser.add_argument(
                'path',
                help="The path to a page to update specifically",
                nargs='?')
        parser.add_argument(
                '--single-threaded',
                help="Run in single-threaded mode",
                action='store_true')

    def run(self, ctx):
        if ctx.args.path:
            ctx.wiki.updatePage(path=ctx.args.path)
        else:
            parallel = not ctx.args.single_threaded
            ctx.wiki.updateAll(parallel=parallel)

        if ctx.args.debug and ctx.args.path:
            page_info = ctx.wiki.fs.getPageInfo(ctx.args.path)
            if page_info is None:
                logger.debug("No page for path: %s" % ctx.args.path)
                logger.debug("Path doesn't exist, or is ignored.")
                return
            page = ctx.wiki.getPage(page_info.url)
            logger.debug("Page [%s]:" % page.url)
            logger.debug("--- formatted text ---")
            logger.debug(page.getFormattedText())
            logger.debug("--- meta --")
            logger.debug(page.getLocalMeta())
            logger.debug("--- links ---")
            logger.debug(page.getLocalLinks())
            logger.debug("--- resolved text ---")
            logger.debug(page.text)


@register_command
class ResolveCommand(WikkedCommand):
    def __init__(self):
        super(ResolveCommand, self).__init__()
        self.name = 'resolve'
        self.description = (
                "Makes sure that the final page text is resolved "
                "for all pages.")

    def setupParser(self, parser):
        parser.add_argument(
                '-f', '--force',
                help="Force resolve all pages",
                action='store_true')
        parser.add_argument(
                '--parallel',
                help="Run the operation with multiple workers in parallel",
                action='store_true')

    def run(self, ctx):
        ctx.wiki.resolve(
            force=ctx.args.force,
            parallel=ctx.args.parallel)
