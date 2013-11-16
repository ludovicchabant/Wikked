
# Configure a simpler log format.
from wikked import settings
settings.LOG_FORMAT = "[%(levelname)s]: %(message)s"
settings.UPDATE_WIKI_ON_START = False

# Create the app and the wiki.
from wikked.web import app, wiki

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
def user(username=None, password=None):
    """Generates the entry for a new user so you can
       copy/paste it in your `.wikirc`.
    """
    username = username or prompt('Username: ')
    password = password or prompt_pass('Password: ')
    password = app.bcrypt.generate_password_hash(password)
    print "[users]"
    print "%s = %s" % (username, password)


@manager.command
def reset():
    """ Re-generates the database and the full-text-search index.
    """
    wiki.reset()


@manager.command
def update(url=None):
    """ Updates the database and the full-text-search index with any
        changed/new files.
    """
    wiki.update(url)


@manager.command
def list():
    """ Lists page names in the wiki.
    """
    for url in wiki.db.getPageUrls():
        print url


@manager.command
def get(url, resolve=False):
    """ Gets a page that matches the given URL.
    """
    page = wiki.getPage(url)
    if resolve:
        page._force_resolve = True
    print page.text


@manager.command
def linksfrom(url):
    page = wiki.getPage(url)
    for l in page.links:
        print l


@manager.command
def linksto(url):
    page = wiki.getPage(url)
    for l in page.getIncomingLinks():
        print l


if __name__ == "__main__":
    manager.run()
