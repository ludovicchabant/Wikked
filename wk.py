#!/usr/local/bin/python

# Configure logging.
import logging
logging.basicConfig(level=logging.DEBUG)

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
def reset(cache=False, index_only=False):
    """ Re-generates the database and the full-text-search index.
    """
    if index_only:
        wiki.index.reset(wiki.getPages())
    else:
        wiki.reset(cache_ext_data=cache)


@manager.command
def update(url=None, cache=False):
    """ Updates the database and the full-text-search index with any
        changed/new files.
    """
    wiki.update(url, cache_ext_data=cache)


@manager.command
def cache():
    """ Makes sure the extended cache is valid for the whole wiki.
    """
    wiki._cachePages()


@manager.command
def list(fs=False):
    """ Lists page names in the wiki.
    """
    if fs:
        for pi in wiki.fs.getPageInfos():
            print pi.url
    else:
        for url in wiki.db.getPageUrls():
            print url


@manager.command
def get(url, force_resolve=False, rev=None):
    """ Gets a page that matches the given URL.
    """
    page = wiki.getPage(url)
    if force_resolve:
        page._force_resolve = True
    if rev is not None:
        print page.getRevision(rev)
        return
    print page.text


@manager.command
def search(query):
    """ Searches the wiki.
    """
    hits = wiki.index.search(query)
    print hits


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

