import re
import os
import os.path
import urllib.request, urllib.parse, urllib.error
from xml.sax.saxutils import escape, unescape


re_terminal_path = re.compile(r'[/\\]|(\w\:)')
endpoint_regex = re.compile(r'(\w[\w\d]*)\:(.*)')
endpoint_prefix_regex = re.compile(r'^(\w[\w\d]+)\:')


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
        if not path or re_terminal_path.match(path):
            break
    return None


def get_absolute_url(base_url, url, quote=False):
    endpoint, base_url = split_page_url(base_url)
    if base_url[0] != '/':
        raise ValueError("The base URL must be absolute. Got: %s" % base_url)

    if url.startswith('/'):
        # Absolute page URL.
        abs_url = url
    elif url.startswith('./'):
        # URL wants to be relative to the base url's name, instead
        # of its directory.
        abs_url = base_url + url[1:]
    else:
        # Relative page URL. Let's normalize all `..` in it,
        # which could also replace forward slashes by backslashes
        # on Windows, so we need to convert that back.
        urldir = os.path.dirname(base_url)
        raw_abs_url = os.path.join(urldir, url)
        abs_url = os.path.normpath(raw_abs_url).replace('\\', '/')
    if quote:
        abs_url = urllib.parse.quote(abs_url.encode('utf-8'))
    if endpoint:
        return '%s:%s' % (endpoint, abs_url)
    return abs_url


def is_endpoint_url(url):
    return endpoint_prefix_regex.match(url) is not None


def split_page_url(url):
    m = endpoint_regex.match(url)
    if m is None:
        return (None, url)
    endpoint = m.group(1)
    path = m.group(2)
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


def flatten_single_metas(meta):
    items = list(meta.items())
    for k, v in items:
        if isinstance(v, list):
            l = len(v)
            if l == 0:
                del meta[k]
            elif l == 1:
                meta[k] = v[0]
    return meta


html_escape_table = {'"': "&quot;", "'": "&apos;"}
html_unescape_table = {v: k for k, v in list(html_escape_table.items())}

def html_escape(text):
    return escape(text, html_escape_table)


def html_unescape(text):
    return unescape(text, html_unescape_table)

