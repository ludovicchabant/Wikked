import urllib
import string
from flask import g, abort, jsonify
from flask.ext.login import current_user
from wikked.fs import PageNotFoundError
from wikked.utils import split_page_url
from wikked.web import app


DONT_CHECK = 0
CHECK_FOR_READ = 1
CHECK_FOR_WRITE = 2


def url_from_viewarg(url):
    url = urllib.unquote(url)
    endpoint, path = split_page_url(url)
    if endpoint:
        return u'%s:/%s' % (endpoint, path)
    return u'/' + path


def split_url_from_viewarg(url):
    url = urllib.unquote(url)
    endpoint, path = split_page_url(url)
    value = string.rsplit(path, '/', 1)[-1]
    return (endpoint, value, u'/' + path)


def make_page_title(url):
    return url[1:]


def get_page_or_none(url, convert_url=True, check_perms=DONT_CHECK, force_resolve=False):
    if convert_url:
        url = url_from_viewarg(url)
    try:
        page = g.wiki.getPage(url)
    except PageNotFoundError:
        return None

    if force_resolve:
        page._force_resolve = True
    if check_perms == CHECK_FOR_READ and not is_page_readable(page):
        abort(401)
    elif check_perms == CHECK_FOR_WRITE and not is_page_writable(page):
        abort(401)

    return page


def get_page_or_404(url, convert_url=True, check_perms=DONT_CHECK, force_resolve=False):
    page = get_page_or_none(url, convert_url, check_perms, force_resolve)
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
        meta = dict(page.getLocalMeta())
    else:
        meta = dict(page.meta)
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
            'url': urllib.quote(item.encode('utf-8')),
            'name': item
            })
    return result


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

