import os.path
from flask.ext.script import Manager, Command
from wikked import app

manager = Manager(app)

@manager.command
def stats():
    """Prints some stats about the wiki."""
    pass


if __name__ == "__main__":
    manager.run()

