import logging
from wikked.commands.base import WikkedCommand, register_command


logger = logging.getLogger(__name__)


@register_command
class ResetCommand(WikkedCommand):
    def __init__(self):
        super(ResetCommand, self).__init__()
        self.name = 'reset'
        self.description = ("Re-generates the database and the full-text "
                "search index.")

    def setupParser(self, parser):
        parser.add_argument('--indexonly',
                help="Only update the full-text search index",
                action='store_true')

    def run(self, ctx):
        if ctx.args.indexonly:
            ctx.wiki.index.reset(ctx.wiki.getPages())
        else:
            ctx.wiki.reset()


@register_command
class UpdateCommand(WikkedCommand):
    def __init__(self):
        super(UpdateCommand, self).__init__()
        self.name = 'update'
        self.description = ("Updates the database and the full-text-search "
                "index with any changed/new files.")

    def setupParser(self, parser):
        parser.add_argument('url',
                help="The URL of a page to update specifically",
                nargs='?')
        parser.add_argument('--cache',
                help="Re-cache all pages",
                action='store_true')

    def run(self, ctx):
        ctx.wiki.update(ctx.args.url, cache_ext_data=ctx.args.cache)


@register_command
class CacheCommand(WikkedCommand):
    def __init__(self):
        super(CacheCommand, self).__init__()
        self.name = 'cache'
        self.description = ("Makes sure the extended cache is valid for the "
                "whole wiki.")

    def setupParser(self, parser):
        parser.add_argument('-f', '--force',
                help="Force cache all pages",
                action='store_true')
        parser.add_argument('--parallel',
                help="Run the operation with multiple workers in parallel",
                action='store_true')

    def run(self, ctx):
        ctx.wiki._cachePages(
            force_resolve=ctx.args.force,
            parallel=ctx.args.parallel)
