import re
import os
import os.path
import urllib
from xml.sax.saxutils import escape, unescape


endpoint_regex = re.compile(r'(\w[\w\d]*)\:(.*)')


class PageNotFoundError(Exception):
    """ An error raised when no physical file
       is found for a given URL.
    """
    def __init__(self, url, message=None, *args):
        Exception.__init__(self, url, message, *args)

    def __str__(self):
        url = self.args[0]
        message = self.args[1]
        res = "Can't find page '%s'." % url
        if message:
            res += ' ' + message
        return res


class NamespaceNotFoundError(Exception):
    """ An error raised when no physical directory is found
        for a given URL.
    """
    pass


def find_wiki_root(path=None):
    if not path:
        path = os.getcwd()
    while True:
        if os.path.isfile(os.path.join(path, '.wikirc')):
            return path
        if (os.path.isdir(os.path.join(path, '.git')) or
                os.path.isdir(os.path.join(path, '.hg'))):
            return path
        path = os.path.dirname(path)
        if not path or path == '/':
            break
    return None


def get_absolute_url(base_url, url, quote=False):
    base_url = re.sub(r'^(\w[\w\d]+)\:', '', base_url)
    if base_url[0] != '/':
        raise ValueError("The base URL must be absolute. Got: %s" % base_url)

    if url.startswith('/'):
        # Absolute page URL.
        abs_url = url
    else:
        # Relative page URL. Let's normalize all `..` in it,
        # which could also replace forward slashes by backslashes
        # on Windows, so we need to convert that back.
        urldir = os.path.dirname(base_url)
        raw_abs_url = os.path.join(urldir, url)
        abs_url = os.path.normpath(raw_abs_url).replace('\\', '/')
    if quote:
        abs_url = urllib.quote(abs_url.encode('utf-8'))
    return abs_url


def split_page_url(url):
    m = endpoint_regex.match(url)
    if m is None:
        return (None, url)
    endpoint = unicode(m.group(1))
    path = unicode(m.group(2))
    return (endpoint, path)


def get_meta_name_and_modifiers(name):
    """ Strips a meta name from any leading modifiers like `__` or `+`
        and returns both as a tuple. If no modifier was found, the
        second tuple value is `None`.
    """
    clean_name = name
    modifiers = None
    if name[:2] == '__':
        modifiers = '__'
        clean_name = name[3:]
    elif name[0] == '+':
        modifiers = '+'
        clean_name = name[1:]
    return (clean_name, modifiers)


html_escape_table = {'"': "&quot;", "'": "&apos;"}
html_unescape_table = {v: k for k, v in html_escape_table.items()}

def html_escape(text):
    return escape(text, html_escape_table)


def html_unescape(text):
    return unescape(text, html_unescape_table)

