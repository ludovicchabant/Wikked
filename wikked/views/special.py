from flask import g, request
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

    def is_hit_readable(hit):
        page = get_page_or_none(hit['url'])
        return page is None or is_page_readable(page)
    hits = filter(is_hit_readable, g.wiki.index.search(query))
    result = {'query': query, 'hits': hits}
    return make_auth_response(result)

