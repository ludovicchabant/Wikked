import re
import os.path
import unicodedata


def get_absolute_url(base_url, url, do_slugify=True):
    if url.startswith('/'):
        # Absolute page URL.
        abs_url = url[1:]
    else:
        # Relative page URL. Let's normalize all `..` in it,
        # which could also replace forward slashes by backslashes
        # on Windows, so we need to convert that back.
        urldir = os.path.dirname(base_url)
        raw_abs_url = os.path.join(urldir, url)
        abs_url = os.path.normpath(raw_abs_url).replace('\\', '/')
    if do_slugify:
        abs_url_parts = abs_url.split('/')
        abs_url = ''
        for i, part in enumerate(abs_url_parts):
            if i > 0:
                abs_url += '/'
            abs_url += title_to_url(part)
    return abs_url


def title_to_url(title):
    # Remove diacritics (accents, etc.) and replace them with ASCII
    # equivelent.
    ansi_title = ''.join((c for c in
        unicodedata.normalize('NFD', unicode(title))
        if unicodedata.category(c) != 'Mn'))
    # Now replace spaces and punctuation with a hyphen.
    return re.sub(r'[^A-Za-z0-9_\.\-\(\)]+', '-', ansi_title.lower())


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


