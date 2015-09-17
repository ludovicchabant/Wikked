from flask import jsonify, request, abort
from flask.ext.login import current_user
from wikked.web import app, get_wiki
from wikked.webimpl.special import (
        get_orphans, get_broken_redirects, get_double_redirects,
        get_dead_ends, get_search_results, get_search_preview_results)


def call_api(api_func, *args, **kwargs):
    wiki = get_wiki()
    user = current_user.get_id()
    result = api_func(wiki, user, *args, **kwargs)
    return jsonify(result)


@app.route('/api/orphans')
def api_special_orphans():
    return call_api(get_orphans)


@app.route('/api/broken-redirects')
def api_special_broken_redirects():
    return call_api(get_broken_redirects)


@app.route('/api/double-redirects')
def api_special_double_redirects():
    return call_api(get_double_redirects)


@app.route('/api/dead-ends')
def api_special_dead_ends():
    return call_api(get_dead_ends)


@app.route('/api/search')
def api_search():
    query = request.args.get('q')
    if query is None or query == '':
        abort(400)
    return call_api(get_search_results, query=query)


@app.route('/api/searchpreview')
def api_search_preview():
    query = request.args.get('q')
    if query is None or query == '':
        abort(400)
    return call_api(get_search_preview_results, query=query)


