import os.path
import urllib
import string
import datetime
from flask import g, abort, jsonify
from flask.ext.login import current_user
from wikked.fs import PageNotFoundError
from wikked.utils import split_page_url, get_absolute_url
from wikked.web import app, get_wiki


DONT_CHECK = 0
CHECK_FOR_READ = 1
CHECK_FOR_WRITE = 2


def url_from_viewarg(url):
    endpoint, path = split_url_from_viewarg(url)
    if endpoint:
        return u'%s:%s' % (endpoint, path)
    return path


def split_url_from_viewarg(url):
    url = urllib.unquote(url)
    endpoint, path = split_page_url(url)
    if endpoint:
        return (endpoint, path)
    return (None, u'/' + path)


def make_page_title(url):
    return url[1:]


def get_page_or_none(url, fields=None, convert_url=True,
        check_perms=DONT_CHECK):
    if convert_url:
        url = url_from_viewarg(url)

    auto_reload = app.config.get('WIKI_AUTO_RELOAD')
    if auto_reload and fields is not None:
        if 'path' not in fields:
            fields.append('path')
        if 'cache_time' not in fields:
            fields.append('cache_time')
        if 'is_resolved' not in fields:
            fields.append('is_resolved')

    try:
        wiki = get_wiki()
        page = wiki.getPage(url, fields=fields)
    except PageNotFoundError:
        return None

    if auto_reload:
        wiki = get_wiki()
        path_time = datetime.datetime.fromtimestamp(
            os.path.getmtime(page.path))
        if path_time >= page.cache_time:
            app.logger.info("Page '%s' has changed, reloading." % url)
            wiki.updatePage(path=page.path)
            page = wiki.getPage(url, fields=fields)
        elif not page.is_resolved:
            app.logger.info("Page '%s' was not resolved, resolving now." % url)
            wiki.resolve(only_urls=[url])
            wiki.index.updatePage(wiki.db.getPage(
                url, fields=['url', 'path', 'title', 'text']))
            page = wiki.getPage(url, fields=fields)

    if check_perms == CHECK_FOR_READ and not is_page_readable(page):
        abort(401)
    elif check_perms == CHECK_FOR_WRITE and not is_page_writable(page):
        abort(401)

    return page


def get_page_or_404(url, fields=None, convert_url=True,
        check_perms=DONT_CHECK):
    page = get_page_or_none(url, fields, convert_url, check_perms)
    if page is not None:
        return page
    app.logger.error("No such page: " + url)
    abort(404)


def is_page_readable(page, user=current_user):
    return page.wiki.auth.isPageReadable(page, user.get_id())


def is_page_writable(page, user=current_user):
    return page.wiki.auth.isPageWritable(page, user.get_id())


def get_page_meta(page, local_only=False):
    if local_only:
        meta = dict(page.getLocalMeta() or {})
    else:
        meta = dict(page.getMeta() or {})
    meta['title'] = page.title
    meta['url'] = urllib.quote(page.url.encode('utf-8'))
    for name in COERCE_META:
        if name in meta:
            meta[name] = COERCE_META[name](meta[name])
    return meta


def get_category_meta(category):
    result = []
    for item in category:
        result.append({
            'url': u'category:/' + urllib.quote(item.encode('utf-8')),
            'name': item
            })
    return result


class CircularRedirectError(Exception):
    def __init__(self, url, visited):
        super(CircularRedirectError, self).__init__(
                "Circular redirect detected at '%s' "
                "after visiting: %s" % (url, visited))


class RedirectNotFound(Exception):
    def __init__(self, url, not_found):
        super(RedirectNotFound, self).__init__(
                "Target redirect page '%s' not found from '%s'." %
                (url, not_found))


def get_redirect_target(path, fields=None, convert_url=False,
                        check_perms=DONT_CHECK, first_only=False):
    page = None
    orig_path = path
    visited_paths = []

    while True:
        page = get_page_or_none(
                path,
                fields=fields,
                convert_url=convert_url,
                check_perms=check_perms)
        if page is None:
            raise RedirectNotFound(orig_path, path)

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


def make_auth_response(data):
    if current_user.is_authenticated():
        data['auth'] = {
                'username': current_user.username,
                'is_admin': current_user.is_admin()
                }
    return jsonify(data)


def get_or_build_pagelist(list_name, builder, fields=None):
    # If the wiki is using background jobs, we can accept invalidated
    # lists... it just means that a background job is hopefully still
    # just catching up.
    # Otherwise, everything is synchronous and we need to build the
    # list if needed.
    wiki = get_wiki()
    build_inline = not app.config['WIKI_ASYNC_UPDATE']
    page_list = wiki.db.getPageListOrNone(list_name, fields=fields,
                                          valid_only=build_inline)
    if page_list is None and build_inline:
        app.logger.info("Regenerating list: %s" % list_name)
        page_list = builder()
        wiki.db.addPageList(list_name, page_list)

    return page_list


def get_generic_pagelist_builder(filter_func, fields=None):
    fields = fields or ['url', 'title', 'meta']
    def builder():
        # Make sure all pages have been resolved.
        wiki = get_wiki()
        wiki.resolve()

        pages = []
        for page in wiki.getPages(
                no_endpoint_only=True,
                fields=fields):
            try:
                if filter_func(page):
                    pages.append(page)
            except Exception as e:
                app.logger.error("Error while inspecting page: %s" % page.url)
                app.logger.error("   %s" % e)
        return pages
    return builder

