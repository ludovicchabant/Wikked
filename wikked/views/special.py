from flask import g, jsonify, request, abort
from wikked.views import (
    is_page_readable, get_page_meta, get_page_or_none,
    get_or_build_pagelist, get_generic_pagelist_builder,
    get_redirect_target, CircularRedirectError, RedirectNotFound)
from wikked.utils import get_absolute_url
from wikked.web import app, get_wiki


def build_pagelist_view_data(pages):
    pages = sorted(pages, key=lambda p: p.url)
    data = [get_page_meta(p) for p in pages if is_page_readable(p)]
    result = {'pages': data}
    return jsonify(result)


def generic_pagelist_view(list_name, filter_func, fields=None):
    fields = fields or ['url', 'title', 'meta']
    pages = get_or_build_pagelist(
            list_name,
            get_generic_pagelist_builder(filter_func, fields),
            fields=fields)
    return build_pagelist_view_data(pages)


@app.route('/api/orphans')
def api_special_orphans():
    def builder_func():
        wiki = get_wiki()
        wiki.resolve()

        pages = {}
        rev_links = {}
        for p in wiki.getPages(
                no_endpoint_only=True,
                fields=['url', 'title', 'meta', 'links']):
            pages[p.url] = p
            rev_links[p.url] = 0

            for l in p.links:
                abs_l = get_absolute_url(p.url, l)
                cnt = rev_links.get(abs_l, 0)
                rev_links[abs_l] = cnt + 1

        or_pages = []
        for tgt, cnt in rev_links.iteritems():
            if cnt == 0:
                or_pages.append(pages[tgt])
        return or_pages

    fields = ['url', 'title', 'meta', 'links']
    pages = get_or_build_pagelist('orphans', builder_func, fields)
    return build_pagelist_view_data(pages)


@app.route('/api/broken-redirects')
def api_special_broken_redirects():
    def filter_func(page):
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

    return generic_pagelist_view('broken_redirects', filter_func)


@app.route('/api/double-redirects')
def api_special_double_redirects():
    def builder_func():
        wiki = get_wiki()
        wiki.resolve()

        pages = {}
        redirs = {}
        for p in wiki.getPages(
                no_endpoint_only=True,
                fields=['url', 'title', 'meta']):
            pages[p.url] = p

            target = p.getMeta('redirect')
            if target:
                target = get_absolute_url(p.url, target)
                redirs[p.url] = target

        dr_pages = []
        for src, tgt in redirs.iteritems():
            if tgt in redirs:
                dr_pages.append(pages[src])
        return dr_pages

    fields = ['url', 'title', 'meta']
    pages = get_or_build_pagelist('double_redirects', builder_func, fields)
    return build_pagelist_view_data(pages)


@app.route('/api/dead-ends')
def api_special_dead_ends():
    def filter_func(page):
        return len(page.links) == 0

    return generic_pagelist_view(
            'dead_ends', filter_func,
            fields=['url', 'title', 'meta', 'links'])


@app.route('/api/search')
def api_search():
    query = request.args.get('q')
    if query is None or query == '':
        abort(400)

    readable_hits = []
    wiki = get_wiki()
    hits = list(wiki.index.search(query))
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
    wiki = get_wiki()
    hits = list(wiki.index.previewSearch(query))
    for h in hits:
        page = get_page_or_none(h.url, convert_url=False)
        if page is not None and is_page_readable(page):
            readable_hits.append({'url': h.url, 'title': h.title})

    result = {
            'query': query,
            'hit_count': len(readable_hits),
            'hits': readable_hits}
    return jsonify(result)

