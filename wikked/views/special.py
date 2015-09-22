from flask import render_template
from flask.ext.login import current_user
from wikked.views import (
        requires_reader_auth,
        add_auth_data, add_navigation_data)
from wikked.web import app, get_wiki
from wikked.webimpl.special import (
        get_orphans, get_broken_redirects, get_double_redirects,
        get_dead_ends)


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
            "url": "/special/history",
            "description": "See all changes in the wiki.",
            "section": "wiki",
            },
        'orphans': {
            "title": "Orphaned Pages",
            "url": "/special/list/orphans",
            "description": ("Lists pages in the wiki that have no "
                            "links to them."),
            "section": "lists",
            "template": "special-orphans.html"
            },
        'broken-redirects': {
            "title": "Broken Redirects",
            "url": "/special/list/broken-redirects",
            "description": ("Lists pages that redirect to a missing "
                            "page."),
            "section": "lists",
            "template": "special-broken-redirects.html"
            },
        'double-redirects': {
            "title": "Double Redirects",
            "url": "/special/list/double-redirects",
            "description": "Lists pages that redirect twice or more.",
            "section": "lists",
            "template": "special-double-redirects.html"
            },
        'dead-ends': {
            "title": "Dead-End Pages",
            "url": "/special/list/dead-ends",
            "description": ("Lists pages that don't have any "
                            "outgoing links."),
            "section": "lists",
            "template": "special-dead-ends.html"
            },
        'users': {
            "title": "All Users",
            "url": "/special/users",
            "description": "A list of all registered users.",
            "section": "users",
            }
        }


@app.route('/special')
@requires_reader_auth
def special_pages_dashboard():
    data = {
            'is_special_page': True,
            'sections': []}
    for info in special_sections:
        sec = {'title': info['title'], 'pages': []}
        for k, p in special_pages.items():
            if p['section'] == info['name']:
                sec['pages'].append(p)
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

    data = api_func(wiki, user, *args, **kwargs)
    add_auth_data(data)
    add_navigation_data(None, data, raw_url=raw_url)
    data['title'] = info['title']
    data['is_special_page'] = True
    return render_template(info['template'], **data)


@app.route('/special/list/orphans')
@requires_reader_auth
def special_list_orphans():
    return call_api('orphans', get_orphans,
                    raw_url='/api/orphans')


@app.route('/special/list/broken-redirects')
@requires_reader_auth
def special_list_broken_redirects():
    return call_api('broken-redirects', get_broken_redirects,
                    raw_url='/api/broken-redirects')


@app.route('/special/list/double-redirects')
@requires_reader_auth
def special_list_double_redirects():
    return call_api('double-redirects', get_double_redirects,
                    raw_url='/api/double-redirects')


@app.route('/special/list/dead-ends')
@requires_reader_auth
def special_list_dead_ends():
    return call_api('dead-ends', get_dead_ends,
                    raw_url='/api/dead-ends')

