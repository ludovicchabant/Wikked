import re
import os
import os.path
import unicodedata
from xml.sax.saxutils import escape, unescape


class PageNotFoundError(Exception):
    """ An error raised when no physical file
       is found for a given URL.
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


def get_absolute_url(base_url, url, do_slugify=True):
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
    if do_slugify:
        abs_url = namespace_title_to_url(abs_url)
    return abs_url


def namespace_title_to_url(url):
    url_parts = url.split('/')
    result = ''
    if url[0] == '/':
        result = '/'
        url_parts = url_parts[1:]
    for i, part in enumerate(url_parts):
        if i > 0:
            result += '/'
        result += title_to_url(part)
    return result


def title_to_url(title):
    # Remove diacritics (accents, etc.) and replace them with ASCII
    # equivelent.
    ansi_title = ''.join((c for c in
        unicodedata.normalize('NFD', unicode(title))
        if unicodedata.category(c) != 'Mn'))
    # Now replace spaces and punctuation with a hyphen.
    return re.sub(r'[^A-Za-z0-9_\.\-\(\)\{\}]+', '-', ansi_title.lower())


def path_to_url(path, strip_ext=True):
    if strip_ext:
        path = os.path.splitext(path)[0]

    url = ''
    parts = path.lower().split(os.sep) # unicode(path)
    for i, part in enumerate(parts):
        url += '/' + title_to_url(part)
    return url


def url_to_title(url):
    def upperChar(m):
        return m.group(0).upper()
    return re.sub(r'^.|\s\S', upperChar, url.lower().replace('-', ' '))


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

