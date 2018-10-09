from flask import request, redirect, url_for, render_template, abort
from flask_login import current_user
from wikked.views import add_auth_data, add_navigation_data
from wikked.web import app, get_wiki
from wikked.webimpl.decorators import requires_permission
from wikked.webimpl.special import (
        get_orphans, get_broken_redirects, get_double_redirects,
        get_dead_ends, get_broken_links, get_wanted_pages)


special_sections = [
    {
        'name': 'wiki',
        'title': 'Wiki'
    },
    {
        'name': 'lists',
        'title': 'Page Lists'
    },
    {
        'name': 'users',
        'title': 'Users'
    }
]

special_pages = {
    'changes': {
        "title": "Recent Changes",
        "view": 'site_history',
        "description": "See all changes in the wiki.",
        "section": "wiki",
    },
    'orphans': {
        "title": "Orphaned Pages",
        "view": 'special_list_orphans',
        "description": ("Lists pages in the wiki that have no "
                        "links to them."),
        "section": "lists",
        "template": "special-orphans.html"
    },
    'broken-redirects': {
        "title": "Broken Redirects",
        "view": 'special_list_broken_redirects',
        "description": ("Lists pages that redirect to a missing "
                        "page."),
        "section": "lists",
        "template": "special-broken-redirects.html"
    },
    'double-redirects': {
        "title": "Double Redirects",
        "view": 'special_list_double_redirects',
        "description": "Lists pages that redirect twice or more.",
        "section": "lists",
        "template": "special-double-redirects.html"
    },
    'dead-ends': {
        "title": "Dead Ends",
        "view": 'special_list_dead_ends',
        "description": ("Lists pages that don't have any "
                        "outgoing links."),
        "section": "lists",
        "template": "special-dead-ends.html"
    },
    'broken-links': {
        "title": "Broken Links",
        "view": 'special_list_broken_links',
        "description": ("Lists pages that have broken links in them."),
        "section": "lists",
        "template": "special-broken-links.html"
    },
    'wanted-pages': {
        "title": "Wanted Pages",
        "view": 'special_list_wanted_pages',
        "description": ("Lists pages that don't exist yet but already have "
                        "incoming links to them."),
        "section": "lists",
        "template": "special-wanted-pages.html"
    },
    'users': {
        "title": "All Users",
        "view": 'special_users',
        "description": "A list of all registered users.",
        "section": "users",
    }
}


@app.route('/read/special:/Dashboard')
@requires_permission('read')
def special_pages_dashboard():
    data = {
            'is_special_page': True,
            'sections': []}
    for info in special_sections:
        sec = {'title': info['title'], 'pages': []}
        for k, p in special_pages.items():
            if p['section'] == info['name']:
                pdata = p.copy()
                pdata['url'] = url_for(pdata['view'])
                sec['pages'].append(pdata)
        sec['pages'] = sorted(sec['pages'], key=lambda i: i['title'])
        data['sections'].append(sec)

    add_auth_data(data)
    add_navigation_data(None, data)
    return render_template('special-pages.html', **data)


def call_api(page_name, api_func, *args, **kwargs):
    wiki = get_wiki()
    user = current_user.get_id()
    info = special_pages[page_name]

    raw_url = None
    if 'raw_url' in kwargs:
        raw_url = kwargs['raw_url']
        del kwargs['raw_url']
    refresh = True
    if 'refresh' in kwargs:
        refresh = kwargs['refresh']
        del kwargs['refresh']

    data = api_func(wiki, user, *args, **kwargs)
    add_auth_data(data)
    add_navigation_data(None, data, raw_url=raw_url)
    data['title'] = info['title']
    data['is_special_page'] = True
    if refresh:
        data['refresh'] = {
            'url': url_for('special_list_refresh'),
            'list_name': page_name.replace('-', '_'),
            'postback': page_name
        }
    return render_template(info['template'], **data)


@app.route('/read/special:/Orphaned Pages')
@requires_permission('read')
def special_list_orphans():
    return call_api('orphans', get_orphans,
                    raw_url='/api/orphans')


@app.route('/read/special:/Broken Redirects')
@requires_permission('read')
def special_list_broken_redirects():
    return call_api('broken-redirects', get_broken_redirects,
                    raw_url='/api/broken-redirects')


@app.route('/read/special:/Double Redirects')
@requires_permission('read')
def special_list_double_redirects():
    return call_api('double-redirects', get_double_redirects,
                    raw_url='/api/double-redirects')


@app.route('/read/special:/Dead Ends')
@requires_permission('read')
def special_list_dead_ends():
    return call_api('dead-ends', get_dead_ends,
                    raw_url='/api/dead-ends')


@app.route('/read/special:/Broken Links')
@requires_permission('read')
def special_list_broken_links():
    return call_api('broken-links', get_broken_links,
                    raw_url='/api/broken-links')


@app.route('/read/special:/Wanted Pages')
@requires_permission('read')
def special_list_wanted_pages():
    return call_api('wanted-pages', get_wanted_pages,
                    raw_url='/api/wanted-pages',
                    refresh=False)


@app.route('/special/list-refresh', methods=['POST'])
@requires_permission('listrefresh')
def special_list_refresh():
    list_name = request.form.get('list_name')
    postback_name = request.form.get('postback')
    if not list_name:
        abort(400)

    info = special_pages.get(postback_name)
    if not info:
        abort(400)

    postback_url = url_for(info['view'])

    wiki = get_wiki()
    wiki.db.removePageList(list_name)

    return redirect(postback_url)
