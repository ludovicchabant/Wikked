from flask import g, jsonify, request, abort
from wikked.views import (
    is_page_readable, get_page_meta, get_page_or_none,
    get_or_build_pagelist, get_generic_pagelist_builder,
    get_redirect_target, CircularRedirectError, RedirectNotFound)
from wikked.utils import get_absolute_url
from wikked.web import app


def orphans_filter_func(page):
    for link in page.getIncomingLinks():
        return False
    return True


def broken_redirects_filter_func(page):
    redirect_meta = page.getMeta('redirect')
    if redirect_meta is None:
        return False

    path = get_absolute_url(page.url, redirect_meta)
    try:
        target, visited = get_redirect_target(
                path,
                fields=['url', 'meta'])
    except CircularRedirectError:
        return True
    except RedirectNotFound:
        return True
    return False


def generic_pagelist_view(list_name, filter_func):
    pages = get_or_build_pagelist(
            list_name,
            get_generic_pagelist_builder(filter_func),
            fields=['url', 'title', 'meta'])
    data = [get_page_meta(p) for p in pages if is_page_readable(p)]
    result = {'pages': data}
    return jsonify(result)


@app.route('/api/orphans')
def api_special_orphans():
    return generic_pagelist_view('orphans', orphans_filter_func)


@app.route('/api/broken-redirects')
def api_special_broken_redirects():
    return generic_pagelist_view('broken_redirects',
                                 broken_redirects_filter_func)


@app.route('/api/search')
def api_search():
    query = request.args.get('q')
    if query is None or query == '':
        abort(400)

    readable_hits = []
    hits = list(g.wiki.index.search(query))
    for h in hits:
        page = get_page_or_none(h.url, convert_url=False)
        if page is not None and is_page_readable(page):
            readable_hits.append({
                    'url': h.url,
                    'title': h.title,
                    'text': h.hl_text})

    result = {
            'query': query,
            'hit_count': len(readable_hits),
            'hits': readable_hits}
    return jsonify(result)


@app.route('/api/searchpreview')
def api_searchpreview():
    query = request.args.get('q')
    if query is None or query == '':
        abort(400)

    readable_hits = []
    hits = list(g.wiki.index.previewSearch(query))
    for h in hits:
        page = get_page_or_none(h.url, convert_url=False)
        if page is not None and is_page_readable(page):
            readable_hits.append({'url': h.url, 'title': h.title})

    result = {
            'query': query,
            'hit_count': len(readable_hits),
            'hits': readable_hits}
    return jsonify(result)

