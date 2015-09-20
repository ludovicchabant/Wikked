from flask import request
from flask.ext.login import current_user
from wikked.web import app


def add_auth_data(data):
    username = current_user.get_id()
    if current_user.is_authenticated():
        user_page_url = 'user:/%s' % username.title()
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
        url, data,
        read=False, edit=False, history=False, inlinks=False,
        raw_url=None, extras=None, footers=None):
    if url is not None:
        url = url.lstrip('/')
    elif read or edit or history or inlinks:
        raise Exception("Default navigation entries require a valid URL.")

    nav = {'home': '/', 'extras': [], 'footers': []}

    nav['is_menu_active'] = (
            request.cookies.get('wiki-menu-active') == '1')

    if read:
        nav['url_read'] = '/read/%s' % url
    if edit:
        nav['url_edit'] = '/edit/%s' % url
    if history:
        nav['url_hist'] = '/hist/%s' % url

    if inlinks:
        nav['extras'].append({
            'title': "Pages Linking Here",
            'url': '/inlinks/' + url,
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
            'url': '/special',
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

