import urllib.parse
from flask import request, url_for
from flask.ext.login import current_user
from wikked.utils import get_url_folder


def add_auth_data(data):
    username = current_user.get_id()
    if current_user.is_authenticated():
        user_page_url = 'user:/%s' % urllib.parse.quote(username.title())
        data['auth'] = {
                'is_logged_in': True,
                'username': username,
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
        read=False, edit=False, history=False, inlinks=False, upload=False,
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
        url_folder = get_url_folder(url).lstrip('/')
        nav['url_new'] = url_for('create_page', url_folder=url_folder)
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

    if upload:
        nav['extras'].append({
            'title': "Upload File",
            'url': url_for('upload_file', p=url),
            'icon': 'upload'
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
