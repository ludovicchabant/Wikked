
# Configure a simpler log format.
from wikked import settings
settings.LOG_FORMAT = "[%(levelname)s]: %(message)s"
settings.UPDATE_WIKI_ON_START = False

# Create the app and the wiki.
from wikked.web import app, wiki
from wikked.page import Page
from wikked.db import conn_scope

# Create the manager.
from flask.ext.script import Manager, prompt, prompt_pass
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
def reset():
    """ Re-generates the database and the full-text-search index.
    """
    with conn_scope(wiki.db):
        wiki.db.reset(wiki.getPages(from_db=False, factory=Page.factory))
        wiki.index.reset(wiki.getPages())


@manager.command
def update():
    """ Updates the database and the full-text-search index with any
        changed/new files.
    """
    with conn_scope(wiki.db):
        wiki.db.update(wiki.getPages(from_db=False, factory=Page.factory))
        wiki.index.update(wiki.getPages())


@manager.command
def list():
    """ Lists page names in the wiki.
    """
    for url in wiki.db.getPageUrls():
        print url


@manager.command
def get(url):
    """ Gets a page that matches the given URL.
    """
    with conn_scope(wiki.db):
        page = wiki.getPage(url)
        print page.text


if __name__ == "__main__":
    manager.run()
