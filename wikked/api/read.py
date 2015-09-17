from flask import request, jsonify, make_response, abort
from flask.ext.login import current_user
from wikked.scm.base import STATE_NAMES
from wikked.utils import PageNotFoundError
from wikked.web import app, get_wiki
from wikked.webimpl import (
        CHECK_FOR_READ,
        url_from_viewarg,
        get_page_or_raise, get_page_or_none,
        get_page_meta, is_page_readable,
        RedirectNotFound, CircularRedirectError)
from wikked.webimpl.read import (
        read_page, get_incoming_links, get_outgoing_links)
from wikked.webimpl.special import list_pages


@app.route('/api/list')
def api_list_all_pages():
    return api_list_pages(None)


@app.route('/api/list/<path:url>')
def api_list_pages(url):
    wiki = get_wiki()
    url = url_from_viewarg(url)
    result = list_pages(wiki, current_user.get_id(), url=url)
    return jsonify(result)


@app.route('/api/read/')
def api_read_main_page():
    wiki = get_wiki()
    return api_read_page(wiki.main_page_url.lstrip('/'))


@app.route('/api/read/<path:url>')
def api_read_page(url):
    wiki = get_wiki()
    user = current_user.get_id()
    try:
        result = read_page(wiki, user, url)
        return jsonify(result)
    except RedirectNotFound as e:
        app.logger.exception(e)
        abort(404)
    except CircularRedirectError as e:
        app.logger.exception(e)
        abort(409)


@app.route('/api/raw/')
def api_read_main_page_raw():
    wiki = get_wiki()
    return api_read_page_raw(wiki.main_page_url.lstrip('/'))


@app.route('/api/raw/<path:url>')
def api_read_page_raw(url):
    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)
    try:
        page = get_page_or_raise(
                wiki, url,
                check_perms=(user, CHECK_FOR_READ),
                fields=['raw_text', 'meta'])
    except PageNotFoundError as e:
        app.logger.exception(e)
        abort(404)
    resp = make_response(page.raw_text)
    resp.mimetype = 'text/plain'
    return resp


@app.route('/api/query')
def api_query():
    wiki = get_wiki()
    query = dict(request.args)
    pages = wiki.getPages(meta_query=query)
    result = {
            'query': query,
            'pages': [get_page_meta(p) for p in pages]
            }
    return jsonify(result)


@app.route('/api/state/')
def api_get_main_page_state():
    wiki = get_wiki()
    return api_get_state(wiki.main_page_url.lstrip('/'))


@app.route('/api/state/<path:url>')
def api_get_state(url):
    wiki = get_wiki()
    user = current_user.get_id()
    page = get_page_or_raise(
            wiki, url,
            check_perms=(user, CHECK_FOR_READ),
            fields=['url', 'title', 'path', 'meta'])
    state = page.getState()
    return jsonify({
        'meta': get_page_meta(page, True),
        'state': STATE_NAMES[state]
        })


@app.route('/api/outlinks/')
def api_get_main_page_outgoing_links():
    wiki = get_wiki()
    return api_get_outgoing_links(wiki.main_page_url.lstrip('/'))


@app.route('/api/outlinks/<path:url>')
def api_get_outgoing_links(url):
    wiki = get_wiki()
    user = current_user.get_id()
    result = get_outgoing_links(wiki, user, url)
    return jsonify(result)


@app.route('/api/inlinks/')
def api_get_main_page_incoming_links():
    wiki = get_wiki()
    return api_get_incoming_links(wiki.main_page_url.lstrip('/'))


@app.route('/api/inlinks/<path:url>')
def api_get_incoming_links(url):
    wiki = get_wiki()
    user = current_user.get_id()
    result = get_incoming_links(wiki, user, url)
    return jsonify(result)


