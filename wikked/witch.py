import sys
import os.path
import logging
import argparse
import datetime
import colorama
from wikked.commands.base import command_classes
from wikked.utils import find_wiki_root
from wikked.wiki import Wiki, WikiParameters


logger = logging.getLogger(__name__)


class ColoredFormatter(logging.Formatter):
    COLORS = {
            'DEBUG': colorama.Fore.BLACK + colorama.Style.BRIGHT,
            'INFO': '',
            'WARNING': colorama.Fore.YELLOW,
            'ERROR': colorama.Fore.RED,
            'CRITICAL': colorama.Back.RED + colorama.Fore.WHITE
            }

    def __init__(self, fmt=None, datefmt=None):
        logging.Formatter.__init__(self, fmt, datefmt)

    def format(self, record):
        color = self.COLORS.get(record.levelname)
        res = logging.Formatter.format(self, record)
        if color:
            res = color + res + colorama.Style.RESET_ALL
        return res


class WitchContext(object):
    def __init__(self, params, wiki, args):
        self.params = params
        self.wiki = wiki
        self.args = args


def main():
    # Setup logging first, even before arg parsing, so we really get
    # all the messages.
    arg_log = False
    arg_debug = False
    arg_quiet = False
    arg_debug_sql = False
    arg_version = False
    for i, arg in enumerate(sys.argv[1:]):
        if not arg.startswith('--'):
            break
        elif arg == '--debug':
            arg_debug = True
        elif arg == '--quet':
            arg_quiet = True
        elif arg == '--log':
            arg_log = sys.argv[i+1]
            i += 1
        elif arg == '--debugsql':
            arg_debug_sql = True
        elif arg == '--version':
            arg_version = True

    if arg_version:
        return print_version()
    if arg_debug and arg_quiet:
        raise Exception("You can't specify both --debug and --quiet.")
    root_logger = logging.getLogger()
    if arg_quiet:
        root_logger.setLevel(logging.WARNING)
    elif arg_debug:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)
    if arg_log:
        from logging.handlers import FileHandler
        root_logger.addHandler(FileHandler(arg_log))
    if arg_debug_sql:
        logging.getLogger('sqlalchemy').setLevel(logging.INFO)

    # Setup the parser.
    parser = argparse.ArgumentParser(
            description="Wikked command line utility")
    parser.add_argument('--root',
            help="Use the specified root directory instead of the current one")
    parser.add_argument('--debug',
            help="Show debug information",
            action='store_true')
    parser.add_argument('--debugsql',
            help="Show debug information for SQLAlchemy (advanced)",
            action='store_true')
    parser.add_argument('--quiet',
            help="Print only important information",
            action='store_true')
    parser.add_argument('--log',
            help="Send log messages to the specified file")
    parser.add_argument('--version',
            help="Print version and exit",
            action='store_true')

    # Import the commands.
    # (this creates a PyLint warning but it's OK)
    # pylint: disable=unused-import
    import wikked.commands.manage
    import wikked.commands.query
    import wikked.commands.users
    import wikked.commands.web

    # Setup the command parsers.
    subparsers = parser.add_subparsers()
    commands = [cls() for cls in command_classes]
    logger.debug("Got %d commands." % len(commands))
    for c in commands:
        cp = subparsers.add_parser(c.name, help=c.description)
        c.setupParser(cp)
        cp.set_defaults(func=c._doRun)

    # Parse!
    result = parser.parse_args()

    # Print the help if no command was specified.
    if not hasattr(result, 'func'):
        parser.print_help()
        return 0

    # Create the wiki.
    root = find_wiki_root(result.root)
    if root:
        params = WikiParameters(root)
        wiki = Wiki(params)
        wiki.start()
    else:
        params = None
        wiki = None

    # Run the command!
    before = datetime.datetime.now()
    try:
        ctx = WitchContext(params, wiki, result)
        exit_code = result.func(ctx)
        if exit_code is not None:
            return exit_code
        return 0
    except Exception as e:
        if result.debug:
            logger.critical("Critical error while running witch command:")
            logger.exception(e)
        else:
            logger.error(e)
        return -1
    finally:
        after = datetime.datetime.now()
        delta = after - before
        logger.debug("Ran command in %fs" % delta.total_seconds())


def print_version():
    if os.path.isdir(os.path.join(os.path.dirname(__file__), '..', '.hg')):
        print("Wikked (development version)")
        return 0
    try:
        from wikked.__version__ import version
    except ImportError:
        print("Can't find version information.")
        return 1
    print("Wikked %s" % version)
    return 0


def real_main():
    colorama.init()
    root_logger = logging.getLogger()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(ColoredFormatter('%(message)s'))
    root_logger.addHandler(handler)

    main()
