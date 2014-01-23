

command_classes = []


def register_command(cls):
    command_classes.append(cls)
    return cls


class WikkedCommand(object):
    def __init__(self):
        self.name = None
        self.description = None
        self.requires_wiki = True

    def setupParser(self, parser):
        raise NotImplementedError()

    def run(self, ctx):
        raise NotImplementedError()

    def _doRun(self, ctx):
        if ctx.wiki is None and self.requires_wiki:
            raise Exception("No wiki found here.")
        result = self.run(ctx)
        if result is None:
            result = 0
        return result


# Import the commands.
# (this creates a PyLint warning but it's OK)
# pylint: disable=unused-import
import wikked.commands.manage
import wikked.commands.query
import wikked.commands.users
import wikked.commands.web

