import logging
from wikked.commands.base import WikkedCommand, register_command


logger = logging.getLogger(__name__)


@register_command
class ListCommand(WikkedCommand):
    def __init__(self):
        super(ListCommand, self).__init__()
        self.name = 'list'
        self.description = "Lists page names in the wiki."

    def setupParser(self, parser):
        parser.add_argument(
                '--fs',
                help="Lists pages by scanning the file-system directly",
                action='store_true')

    def run(self, ctx):
        if ctx.args.fs:
            for pi in ctx.wiki.fs.getPageInfos():
                logger.info(pi.url)
        else:
            for url in ctx.wiki.db.getPageUrls():
                logger.info(url)


@register_command
class GetCommand(WikkedCommand):
    def __init__(self):
        super(GetCommand, self).__init__()
        self.name = 'get'
        self.description = "Gets a page that matches the given URL."

    def setupParser(self, parser):
        parser.add_argument(
                'url',
                help="The URL of the page to get",
                nargs=1)
        parser.add_argument(
                '--raw',
                help="Get the raw text of the page.",
                action='store_true')
        parser.add_argument(
                '--rev',
                help="The revision to get",
                nargs=1)

    def run(self, ctx):
        page = ctx.wiki.getPage(ctx.args.url[0])
        if ctx.args.rev is not None:
            logger.info(page.getRevision(ctx.args.rev))
            return
        if ctx.args.raw:
            logger.info(page.raw_text)
        else:
            logger.info(page.text)


@register_command
class SearchCommand(WikkedCommand):
    def __init__(self):
        super(SearchCommand, self).__init__()
        self.name = 'search'
        self.description = "Searches the wiki."

    def setupParser(self, parser):
        parser.add_argument(
                'query',
                help="The search query",
                nargs='+')

    def run(self, ctx):
        query = ' '.join(ctx.args.query)
        hits = ctx.wiki.index.search(query, highlight=False)
        if not hits:
            logger.info("No pages found.")
        else:
            for h in hits:
                logger.info("[[%s]]: %s" % (h.url, h.hl_text))


@register_command
class LinksFromCommand(WikkedCommand):
    def __init__(self):
        super(LinksFromCommand, self).__init__()
        self.name = 'linksfrom'
        self.description = "Gets the links going out from a given page."

    def setupParser(self, parser):
        parser.add_argument(
                'url',
                help="The page from which the links come from",
                nargs=1)

    def run(self, ctx):
        page = ctx.wiki.getPage(ctx.args.url[0])
        for l in page.links:
            logger.info(l)


@register_command
class LinksToCommand(WikkedCommand):
    def __init__(self):
        super(LinksToCommand, self).__init__()
        self.name = 'linksto'
        self.description = "Gets the links going to a given page."

    def setupParser(self, parser):
        parser.add_argument(
                'url',
                help="The page to which the links go to",
                nargs=1)

    def run(self, ctx):
        page = ctx.wiki.getPage(ctx.args.url[0])
        for l in page.getIncomingLinks():
            logger.info(l)

