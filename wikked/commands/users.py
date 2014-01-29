import logging
from flask.ext.script import prompt_pass
from wikked.bcryptfallback import generate_password_hash
from wikked.commands.base import WikkedCommand, register_command


logger = logging.getLogger(__name__)


@register_command
class UsersCommand(WikkedCommand):
    def __init__(self):
        super(UsersCommand, self).__init__()
        self.name = 'users'
        self.description = "Lists users of this wiki."

    def setupParser(self, parser):
        pass

    def run(self, ctx):
        logger.info("Users:")
        for user in ctx.wiki.auth.getUsers():
            logger.info(" - " + user.username)


@register_command
class NewUserCommand(WikkedCommand):
    def __init__(self):
        super(NewUserCommand, self).__init__()
        self.name = 'newuser'
        self.description = ("Generates the entry for a new user so you can "
               "copy/paste it in your `.wikirc`.")

    def setupParser(self, parser):
        parser.add_argument('username', nargs=1)
        parser.add_argument('password', nargs='?')

    def run(self, ctx):
        username = ctx.args.username
        password = ctx.args.password or prompt_pass('Password: ')
        password = generate_password_hash(password)
        logger.info("[users]")
        logger.info("%s = %s" % (username, password))

