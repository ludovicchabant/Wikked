import time
import urllib
from flask import render_template, request, g
from wikked.views import (get_page_meta, get_page_or_404, get_page_or_none,
        is_page_readable, make_auth_response,
        url_from_viewarg, split_url_from_viewarg,
        CHECK_FOR_READ)
from wikked.web import app
from wikked.scm.base import STATE_NAMES


@app.route('/')
def home():
    tpl_name = 'index.html'
    if app.config['DEBUG']:
        tpl_name = 'index-dev.html'
    return render_template(tpl_name, cache_bust=('?%d' % time.time()));


@app.route('/read/<path:url>')
def read():
    tpl_name = 'index.html'
    if app.config['DEBUG']:
        tpl_name = 'index-dev.html'
    return render_template(tpl_name, cache_bust=('?%d' % time.time()));


@app.route('/search')
def search():
    tpl_name = 'index.html'
    if app.config['DEBUG']:
        tpl_name = 'index-dev.html'
    return render_template(tpl_name, cache_bust=('?%d' % time.time()));


@app.route('/api/list')
def api_list_all_pages():
    return api_list_pages(None)


@app.route('/api/list/<path:url>')
def api_list_pages(url):
    pages = filter(is_page_readable, g.wiki.getPages(url_from_viewarg(url)))
    page_metas = [get_page_meta(page) for page in pages]
    result = {'path': url, 'pages': list(page_metas)}
    return make_auth_response(result)


@app.route('/api/read/')
def api_read_main_page():
    return api_read_page(g.wiki.main_page_url.lstrip('/'))


@app.route('/api/read/<path:url>')
def api_read_page(url):
    #TODO: remove redundant quoting/spliting/unquoting around here.
    endpoint, value, path = split_url_from_viewarg(url)
    if endpoint is None:
        # Normal page.
        page = get_page_or_404(
                path,
                convert_url=False,
                check_perms=CHECK_FOR_READ,
                force_resolve=('force_resolve' in request.args))

        result = {'meta': get_page_meta(page), 'text': page.text}
        return make_auth_response(result)

    # Meta listing page.
    meta_page_url = '%s:%s' % (endpoint, path)
    info_page = get_page_or_none(
            meta_page_url,
            convert_url=False,
            check_perms=CHECK_FOR_READ,
            force_resolve=('force_resolve' in request.args))

    # Get the list of pages to show here.
    query = {endpoint: [value]}
    pages = g.wiki.getPages(meta_query=query)
    tpl_data = {
            'name': endpoint,
            'value': value,
            'safe_value': urllib.quote(value.encode('utf-8')),
            'pages': [get_page_meta(p) for p in pages]
            # TODO: skip pages that are forbidden for the current user
        }
    if info_page:
        tpl_data['info_text'] = info_page.text

    # Render the final page as the list of pages matching the query,
    # under either a default text, or the text from the meta page.
    text = render_template('meta_page.html', **tpl_data)
    result = {
            'meta_query': endpoint,
            'meta_value': value,
            'query': query,
            'meta': {
                    'url': urllib.quote(meta_page_url.encode('utf-8')),
                    'title': value
                },
            'text': text
        }
    if info_page:
        result['meta'] = get_page_meta(info_page)

    return make_auth_response(result)


@app.route('/api/raw/')
def api_read_main_page_raw():
    return api_read_page_raw(g.wiki.main_page_url.lstrip('/'))


@app.route('/api/raw/<path:url>')
def api_read_page_raw(url):
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ)
    result = {'meta': get_page_meta(page), 'text': page.raw_text}
    return make_auth_response(result)


@app.route('/api/query')
def api_query():
    query = dict(request.args)
    pages = g.wiki.getPages(meta_query=query)
    result = {
            'query': query,
            'pages': [get_page_meta(p) for p in pages]
        }
    return make_auth_response(result)


@app.route('/api/state/')
def api_get_main_page_state():
    return api_get_state(g.wiki.main_page_url.lstrip('/'))


@app.route('/api/state/<path:url>')
def api_get_state(url):
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ)
    state = page.getState()
    return make_auth_response({
        'meta': get_page_meta(page, True),
        'state': STATE_NAMES[state]
        })


@app.route('/api/outlinks/')
def api_get_main_page_outgoing_links():
    return api_get_outgoing_links(g.wiki.main_page_url.lstrip('/'))


@app.route('/api/outlinks/<path:url>')
def api_get_outgoing_links(url):
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ)
    links = []
    for link in page.links:
        other = get_page_or_none(link)
        if other is not None:
            links.append({
                'url': other.url,
                'title': other.title
                })
        else:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'out_links': links}
    return make_auth_response(result)


@app.route('/api/inlinks/')
def api_get_main_page_incoming_links():
    return api_get_incoming_links(g.wiki.main_page_url.lstrip('/'))


@app.route('/api/inlinks/<path:url>')
def api_get_incoming_links(url):
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ)
    links = []
    for link in page.getIncomingLinks():
        other = get_page_or_none(link)
        if other is not None and is_page_readable(other):
            links.append({
                'url': link,
                'title': other.title
                })
        else:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'in_links': links}
    return make_auth_response(result)

