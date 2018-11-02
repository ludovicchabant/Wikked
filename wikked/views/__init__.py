import urllib.parse
from flask import request, url_for
from flask_login import current_user
from wikked.utils import get_url_folder, split_page_url
from wikked.web import app, get_wiki


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
    is_readonly_endpoint = False
    if url is not None:
        url = url.lstrip('/')
        endpoint, _ = split_page_url(url)
        if endpoint:
            epinfo = get_wiki().getEndpoint(endpoint)
            is_readonly_endpoint = (epinfo is not None and epinfo.readonly)
    elif read or edit or history or inlinks:
        raise Exception("Default navigation entries require a valid URL.")

    nav = {'extras': [], 'footers': []}

    nav_locked = request.cookies.get('wiki-nav-locked')
    nav['locked'] = (nav_locked == '1')
    nav['lock_icon'] = 'lock' if nav['locked'] else 'unlock'

    nav['url_help'] = url_for('read', url='help:/Help Contents')

    if home:
        nav['url_home'] = '/'
    if new_page and not is_readonly_endpoint:
        url_folder = get_url_folder(url).lstrip('/')
        nav['url_new'] = url_for('create_page', url_folder=url_folder)
    if read:
        nav['url_read'] = url_for('read', url=url)
    if edit and not is_readonly_endpoint:
        nav['url_edit'] = url_for('edit_page', url=url)
    if history and not is_readonly_endpoint:
        nav['url_hist'] = url_for('page_history', url=url)

    if inlinks:
        nav['extras'].append({
            'title': "Pages Linking Here",
            'url': url_for('incoming_links', url=url),
            'icon': 'link'
            })

    if upload and not is_readonly_endpoint:
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
            'icon': 'tachometer-alt'})

    if extras:
        nav['extras'] = [{'title': e[0], 'url': e[1], 'icon': e[2]}
                         for e in extras]

    if footers:
        nav['footers'] = [{'title': f[0], 'url': f[1], 'icon': f[2]}
                          for f in footers]
    data['nav'] = nav

    data['stylesheet'] = app.config['WIKI_STYLESHEET']
