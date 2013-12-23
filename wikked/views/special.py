from flask import g, request, abort
from wikked.views import (is_page_readable, get_page_meta, get_page_or_none,
        make_auth_response)
from wikked.web import app


@app.route('/api/orphans')
def api_special_orphans():
    orphans = []
    for page in g.wiki.getPages():
        try:
            if not is_page_readable(page):
                continue
            is_orphan = True
            for link in page.getIncomingLinks():
                is_orphan = False
                break
            if is_orphan:
                orphans.append({'path': page.url, 'meta': get_page_meta(page)})
        except Exception as e:
            app.logger.error("Error while inspecting page: %s" % page.url)
            app.logger.error("   %s" % e)

    result = {'orphans': orphans}
    return make_auth_response(result)



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
            readable_hits.append({'url': h.url, 'title': h.title, 'text': h.hl_text})

    result = {'query': query, 'hit_count': len(readable_hits), 'hits': readable_hits}
    return make_auth_response(result)


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

    result = {'query': query, 'hit_count': len(readable_hits), 'hits': readable_hits}
    return make_auth_response(result)

