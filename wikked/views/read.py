import urllib.parse
from flask import (
    render_template, request, abort)
from flask_login import current_user
from wikked.utils import split_page_url, PageNotFoundError
from wikked.views import add_auth_data, add_navigation_data
from wikked.web import app, get_wiki
from wikked.webimpl import (
    url_from_viewarg, make_page_title, RedirectNotFoundError)
from wikked.webimpl.decorators import requires_permission
from wikked.webimpl.read import (
    read_page, get_incoming_links)
from wikked.webimpl.special import get_search_results


@app.route('/')
def home():
    wiki = get_wiki()
    url = wiki.main_page_url.lstrip('/')
    return read(url)


def _make_missing_page_data(url):
    is_readonly_endpoint = False
    endpoint, path = split_page_url(url)
    if endpoint:
        epinfo = get_wiki().getEndpoint(endpoint)
        is_readonly_endpoint = (epinfo is not None and epinfo.readonly)

    data = {
        'endpoint': endpoint,
        'is_readonly': is_readonly_endpoint,
        'meta': {
            'url': url,
            'title': make_page_title(path)
        },
        'format': None
    }
    return data


@app.route('/read/<path:url>')
def read(url):
    wiki = get_wiki()
    url = url_from_viewarg(url)

    user = current_user.get_id()
    no_redirect = 'no_redirect' in request.args
    tpl_name = 'read-page.html'
    try:
        data = read_page(wiki, user, url, no_redirect=no_redirect)
    except PageNotFoundError as pnfe:
        tpl_name = 'read-page-missing.html'
        data = _make_missing_page_data(pnfe.url)
    except RedirectNotFoundError as rnfe:
        tpl_name = 'read-page-missing.html'
        data = _make_missing_page_data(rnfe.url)

    if data['format']:
        custom_head = wiki.custom_heads.get(data['format'], '')
        data['custom_head'] = custom_head

    add_auth_data(data)
    add_navigation_data(
            url, data,
            edit=True, history=True, inlinks=True, upload=True,
            raw_url='/api/raw/' + url.lstrip('/'))
    return render_template(tpl_name, **data)


@app.route('/search')
@requires_permission('search')
def search():
    query = request.args.get('q')
    if query is None or query == '':
        abort(400)

    wiki = get_wiki()
    user = current_user.get_id()
    data = get_search_results(wiki, user, query)
    add_auth_data(data)
    add_navigation_data(
            None, data,
            raw_url='/api/search?%s' % urllib.parse.urlencode({'q': query}))
    return render_template('search-results.html', **data)


@app.route('/inlinks')
def incoming_links_to_main_page():
    wiki = get_wiki()
    return incoming_links(wiki.main_page_url.lstrip('/'))


@app.route('/inlinks/<path:url>')
@requires_permission('read')
def incoming_links(url):
    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)
    data = get_incoming_links(wiki, user, url)
    add_auth_data(data)
    add_navigation_data(
            url, data,
            read=True, edit=True, history=True, upload=True,
            raw_url='/api/inlinks/' + url.lstrip('/'))
    return render_template('inlinks-page.html', **data)
