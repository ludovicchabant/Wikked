import os.path
import re
import logging
import datetime
import urllib.parse
from wikked.auth import PERM_READ, PERM_EDIT, PERM_NAMES
from wikked.utils import (
        get_absolute_url, PageNotFoundError, split_page_url, is_endpoint_url)
from wikked.web import app


logger = logging.getLogger(__name__)


class CircularRedirectError(Exception):
    def __init__(self, url, visited):
        super(CircularRedirectError, self).__init__(
                "Circular redirect detected at '%s' "
                "after visiting: %s" % (url, visited))


class RedirectNotFoundError(Exception):
    def __init__(self, url, not_found):
        super(RedirectNotFoundError, self).__init__(
                "Target redirect page '%s' not found from '%s'." %
                (url, not_found))
        self.origin_url = url
        self.url = not_found


class UserPermissionError(Exception):
    def __init__(self, perm, message):
        super().__init__(message)
        self.perm = perm


def url_from_viewarg(url):
    if is_endpoint_url(url):
        return url
    return '/' + url


def split_url_from_viewarg(url):
    url = urllib.parse.unquote(url)
    endpoint, path = split_page_url(url)
    if endpoint:
        return (endpoint, path)
    return (None, '/' + path)


def get_page_or_raise(wiki, url, fields=None, check_perms=None):
    auto_reload = app.config.get('WIKI_AUTO_RELOAD', False)
    if auto_reload is True and fields is not None:
        if 'path' not in fields:
            fields.append('path')
        if 'cache_time' not in fields:
            fields.append('cache_time')

    async_update = app.config.get('WIKI_ASYNC_UPDATE', False)
    if not async_update and fields is not None:
        if 'is_resolved' not in fields:
            fields.append('is_resolved')

    if check_perms is not None and fields is not None:
        if 'local_meta' not in fields:
            fields.append('local_meta')

    page = wiki.getPage(url, fields=fields)

    if auto_reload:
        path_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(page.path))
        if path_time >= page.cache_time:
            logger.info("Page '%s' has changed, reloading." % url)
            wiki.updatePage(path=page.path)
            page = wiki.getPage(url, fields=fields)

    if not async_update:
        if not page.is_resolved:
            logger.info("Page '%s' was not resolved, resolving now." % url)
            wiki.resolve(only_urls=[url])
            wiki.index.updatePage(wiki.db.getPage(
                url, fields=['url', 'path', 'title', 'text']))
            page = wiki.getPage(url, fields=fields)

    if check_perms is not None:
        user, modes = check_perms

        if 'edit' in modes:
            endpoint, path = split_page_url(url)
            if endpoint:
                epinfo = wiki.getEndpoint(endpoint)
                if epinfo is not None and epinfo.readonly:
                    msg = "The '%s' endpoint is read-only." % endpoint
                    raise UserPermissionError('edit', msg)

        has_page_perm = page.wiki.auth.hasPagePermission
        for mode in modes.split(','):
            if not has_page_perm(page, user, PERM_NAMES[mode]):
                if mode == 'read':
                    msg = "You don't have permissions to read this page."
                elif mode == 'edit':
                    msg = "You don't have permissions to edit this page."
                else:
                    msg = "You don't have the '%s' permission." % mode
                raise UserPermissionError(mode, msg)

    return page


def get_page_or_none(wiki, url, **kwargs):
    try:
        return get_page_or_raise(wiki, url, **kwargs)
    except PageNotFoundError:
        return None


def is_page_readable(page, username):
    return page.wiki.auth.hasPagePermission(page, username, PERM_READ)


def is_page_writable(page, username):
    return page.wiki.auth.hasPagePermission(page, username, PERM_EDIT)


def get_page_meta(page, local_only=False):
    if local_only:
        meta = dict(page.getLocalMeta() or {})
    else:
        meta = dict(page.getMeta() or {})
    meta['title'] = page.title
    meta['url'] = urllib.parse.quote(page.url.encode('utf-8'))
    for name in COERCE_META:
        if name in meta:
            meta[name] = COERCE_META[name](meta[name])
    return meta


def get_category_meta(category):
    result = []
    for item in category:
        result.append({
            'url': 'category:/' + urllib.parse.quote(item.encode('utf-8')),
            'name': item
            })
    return result


def get_redirect_target(wiki, path, fields=None,
                        check_perms=None, first_only=False):
    page = None
    orig_path = path
    visited_paths = []

    while True:
        try:
            page = get_page_or_raise(
                    wiki, path,
                    fields=fields,
                    check_perms=check_perms)
        except PageNotFoundError as pnfe:
            if len(visited_paths) > 0:
                raise RedirectNotFoundError(orig_path, path)
            raise

        visited_paths.append(path)
        redirect_meta = page.getMeta('redirect')
        if redirect_meta is None:
            break

        path = get_absolute_url(path, redirect_meta)
        if first_only:
            visited_paths.append(path)
            break

        if path in visited_paths:
            raise CircularRedirectError(path, visited_paths)

    return page, visited_paths


COERCE_META = {
    'category': get_category_meta
    }


def get_or_build_pagelist(wiki, list_name, builder, fields=None,
                          build_inline=True):
    # If the wiki is using background jobs, we can accept invalidated
    # lists... it just means that a background job is hopefully still
    # just catching up.
    # Otherwise, everything is synchronous and we need to build the
    # list if needed.
    page_list = wiki.db.getPageListOrNone(list_name, fields=fields,
                                          valid_only=build_inline)
    if page_list is None and build_inline:
        logger.info("Regenerating list: %s" % list_name)
        page_list = builder()
        wiki.db.addPageList(list_name, page_list)

    return page_list


def get_generic_pagelist_builder(wiki, filter_func, fields=None):
    fields = fields or ['url', 'title', 'meta']

    def builder():
        # Make sure all pages have been resolved.
        wiki.resolve()

        pages = []
        for page in wiki.getPages(
                no_endpoint_only=True,
                fields=fields):
            try:
                if filter_func(page):
                    pages.append(page)
            except Exception as e:
                logger.error("Error while inspecting page: %s" % page.url)
                logger.error("   %s" % e)
        return pages

    return builder


def make_page_title(url, include_endpoint=False):
    endpoint, path = split_page_url(url)
    last_slash = path.rstrip('/').rfind('/')
    if last_slash < 0 or last_slash == 0:
        title = path.lstrip('/')
    else:
        title = path[last_slash + 1:]
    if include_endpoint and endpoint:
        return '%s: %s' % (endpoint, title)
    return title


def load_mimetype_map():
    mimetype_map = {}
    sep_re = re.compile(r'\s+')
    path = os.path.join(os.path.dirname(__file__), 'mime.types')
    with open(path, 'r') as f:
        for line in f:
            tokens = sep_re.split(line)
            if len(tokens) > 1:
                for t in tokens[1:]:
                    mimetype_map[t] = tokens[0]
    return mimetype_map


mimetype_map = load_mimetype_map()
