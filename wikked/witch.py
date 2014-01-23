import logging
import argparse
from wikked.commands.base import command_classes
from wikked.utils import find_wiki_root
from wikked.wiki import Wiki, WikiParameters


logger = logging.getLogger(__name__)


class WitchContext(object):
    def __init__(self, params, wiki, args):
        self.params = params
        self.wiki = wiki
        self.args = args


def main():
    # Setup the parser.
    parser = argparse.ArgumentParser(
            description="Wikked command line utility")
    parser.add_argument('--root',
            help="Use the specified root directory instead of the current one")
    parser.add_argument('--debug',
            help="Show debug information",
            action='store_true')
    parser.add_argument('--quiet',
            help="Print only important information.",
            action='store_true')
    parser.add_argument('--log',
            help="Send log messages to the specified file.")

    # Setup the command parsers.
    subparsers = parser.add_subparsers()
    commands = map(lambda cls: cls(), command_classes)
    logger.debug("Got %d commands." % len(commands))
    for c in commands:
        cp = subparsers.add_parser(c.name, help=c.description)
        c.setupParser(cp)
        cp.set_defaults(func=c._doRun)

    # Parse!
    result = parser.parse_args()

    # Setup logging.
    root_logger = logging.getLogger()
    if result.debug and result.quiet:
        raise Exception("You can't specify both --debug and --quiet.")
    if result.quiet:
        root_logger.setLevel(logging.WARNING)
    elif result.debug:
        root_logger.setLevel(logging.DEBUG)
    if result.log:
        from logging.handlers import FileHandler
        root_logger.addHandler(FileHandler(result.log))

    # Create the wiki.
    root = find_wiki_root(result.root)
    params = WikiParameters(root)
    wiki = Wiki(params)
    wiki.start()

    # Run the command!
    ctx = WitchContext(params, wiki, result)
    exit_code = result.func(ctx)
    return exit_code

