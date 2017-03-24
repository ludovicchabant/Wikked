import urllib.parse
import functools
from flask import request, render_template, url_for
from flask.ext.login import current_user
from wikked.web import app, get_wiki
from wikked.webimpl import PermissionError


def show_unauthorized_error(error=None, error_details=None, tpl_name=None):
    if error is not None:
        error = str(error)

    data = {}
    if error:
        data['error'] = error
    if error_details:
        data['error_details'] = error_details

    add_auth_data(data)
    add_navigation_data(None, data)
    tpl_name = tpl_name or 'error-unauthorized.html'
    return render_template(tpl_name, **data)


def errorhandling_ui(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except PermissionError as ex:
            return show_unauthorized_error(ex)
    return wrapper


def errorhandling_ui2(tpl_name):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except PermissionError as ex:
                return show_unauthorized_error(ex, tpl_name=tpl_name)
        return wrapper
    return decorator


def requires_auth(group):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            wiki = get_wiki()
            if not wiki.auth.hasPermission(group, current_user.get_id()):
                return show_unauthorized_error()
            return f(*args, **kwargs)
        return wrapper
    return decorator


def requires_reader_auth(f):
    decorator = requires_auth('readers')
    return decorator(f)


def add_auth_data(data):
    username = current_user.get_id()
    if current_user.is_authenticated():
        user_page_url = 'user:/%s' % urllib.parse.quote(username.title())
        data['auth'] = {
                'is_logged_in': True,
                'username': username,
                'is_admin': current_user.is_admin(),
                'url_logout': '/logout',
                'url_profile': '/read/%s' % user_page_url
                }
    else:
        data['auth'] = {
                'is_logged_in': False,
                'url_login': '/login'
                }


def add_navigation_data(
        url, data, *,
        home=True, new_page=True,
        read=False, edit=False, history=False, inlinks=False,
        raw_url=None, extras=None, footers=None):
    if url is not None:
        url = url.lstrip('/')
    elif read or edit or history or inlinks:
        raise Exception("Default navigation entries require a valid URL.")

    nav = {'extras': [], 'footers': []}

    nav['hide_menu'] = (
            request.cookies.get('wiki-hide-nav') == '1')

    if home:
        nav['url_home'] = '/'
    if new_page:
        nav['url_new'] = url_for('edit_new_page')
    if read:
        nav['url_read'] = url_for('read', url=url)
    if edit:
        nav['url_edit'] = url_for('edit_page', url=url)
    if history:
        nav['url_hist'] = url_for('page_history', url=url)

    if inlinks:
        nav['extras'].append({
            'title': "Pages Linking Here",
            'url': url_for('incoming_links', url=url),
            'icon': 'link'
            })

    if raw_url:
        nav['footers'].append({
            'title': "RAW",
            'url': raw_url,
            'icon': 'wrench'
            })

    nav['extras'].append({
            'title': "Special Pages",
            'url': url_for('special_pages_dashboard'),
            'icon': 'dashboard'})

    if extras:
        nav['extras'] = [{'title': e[0], 'url': e[1], 'icon': e[2]}
                         for e in extras]

    if footers:
        nav['footers'] = [{'title': f[0], 'url': f[1], 'icon': f[2]}
                          for f in footers]
    data['nav'] = nav

    if app.config['WIKI_DEV_ASSETS']:
        data['is_dev'] = True
    if app.config['WIKI_DEV_NO_JS']:
        data['no_js'] = True
