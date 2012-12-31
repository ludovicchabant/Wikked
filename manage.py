import os.path
import logging
from flask.ext.script import Manager, Command, prompt, prompt_pass
from wikked import app, wiki


manager = Manager(app)


@manager.command
def users():
    """Lists users of this wiki."""
    print "Users:"
    for user in wiki.auth.getUsers():
        print " - " + user.username
    print ""

@manager.command
def new_user():
    """Generates the entry for a new user so you can
       copy/paste it in your `.wikirc`.
    """
    username = prompt('Username: ')
    password = prompt_pass('Password: ')
    password = app.bcrypt.generate_password_hash(password)
    print "[users]"
    print "%s = %s" % (username, password)


@manager.command
def reset_index():
    """ Re-generates the index, if search is broken
        somehow in your wiki.
    """
    wiki.index.reset(wiki.getPages())


if __name__ == "__main__":
    manager.run()

