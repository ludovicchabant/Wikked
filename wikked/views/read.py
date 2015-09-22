import urllib.parse
from flask import (
        render_template, request, abort)
from flask.ext.login import current_user
from wikked.views import add_auth_data, add_navigation_data, errorhandling_ui
from wikked.web import app, get_wiki
from wikked.webimpl import url_from_viewarg
from wikked.webimpl.read import (
        read_page, get_incoming_links)
from wikked.webimpl.special import get_search_results


@app.route('/')
def home():
    wiki = get_wiki()
    url = wiki.main_page_url.lstrip('/')
    return read(url)


@app.route('/read/<path:url>')
@errorhandling_ui
def read(url):
    wiki = get_wiki()
    url = url_from_viewarg(url)
    user = current_user.get_id()
    no_redirect = 'no_redirect' in request.args
    data = read_page(wiki, user, url, no_redirect=no_redirect)
    add_auth_data(data)
    add_navigation_data(
            url, data,
            edit=True, history=True, inlinks=True,
            raw_url='/api/raw/' + url.lstrip('/'))
    return render_template('read-page.html', **data)


@app.route('/search')
@errorhandling_ui
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
@errorhandling_ui
def incoming_links(url):
    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)
    data = get_incoming_links(wiki, user, url)
    add_auth_data(data)
    add_navigation_data(
            url, data,
            read=True, edit=True, history=True,
            raw_url='/api/inlinks/' + url.lstrip('/'))
    return render_template('inlinks-page.html', **data)

