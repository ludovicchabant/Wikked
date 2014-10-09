import time
import urllib
from flask import (render_template, request, g, jsonify, make_response,
                   abort)
from flask.ext.login import current_user
from wikked.views import (get_page_meta, get_page_or_404, get_page_or_none,
        is_page_readable, get_redirect_target,
        url_from_viewarg, split_url_from_viewarg,
        RedirectNotFound, CircularRedirectError,
        CHECK_FOR_READ)
from wikked.web import app, get_wiki
from wikked.scm.base import STATE_NAMES


@app.route('/')
def home():
    tpl_name = 'index.html'
    if app.config['WIKI_DEV_ASSETS']:
        tpl_name = 'index-dev.html'
    return render_template(tpl_name, cache_bust=('?%d' % time.time()));


@app.route('/read/<path:url>')
def read():
    tpl_name = 'index.html'
    if app.config['WIKI_DEV_ASSETS']:
        tpl_name = 'index-dev.html'
    return render_template(tpl_name, cache_bust=('?%d' % time.time()));


@app.route('/search')
def search():
    tpl_name = 'index.html'
    if app.config['WIKI_DEV_ASSETS']:
        tpl_name = 'index-dev.html'
    return render_template(tpl_name, cache_bust=('?%d' % time.time()));


@app.route('/api/list')
def api_list_all_pages():
    return api_list_pages(None)


@app.route('/api/list/<path:url>')
def api_list_pages(url):
    wiki = get_wiki()
    pages = filter(is_page_readable, wiki.getPages(url_from_viewarg(url)))
    page_metas = [get_page_meta(page) for page in pages]
    result = {'path': url, 'pages': list(page_metas)}
    return jsonify(result)


@app.route('/api/read/')
def api_read_main_page():
    wiki = get_wiki()
    return api_read_page(wiki.main_page_url.lstrip('/'))


@app.route('/api/read/<path:url>')
def api_read_page(url):
    additional_info = {}
    if 'user' in request.args:
        user = current_user
        if user.is_authenticated():
            user_page_url = 'user:' + user.username.title()
            additional_info['user'] = {
                    'username': user.username,
                    'groups': user.groups,
                    'page_url': user_page_url
                    }
        else:
            additional_info['user'] = False

    no_redirect = ('no_redirect' in request.args)

    endpoint, path = split_url_from_viewarg(url)
    if endpoint is None:
        # Normal page.
        try:
            page, visited_paths = get_redirect_target(
                    path,
                    fields=['url', 'title', 'text', 'meta'],
                    convert_url=False,
                    check_perms=CHECK_FOR_READ,
                    first_only=no_redirect)
        except RedirectNotFound as e:
            app.logger.exception(e)
            abort(404)
        except CircularRedirectError as e:
            app.logger.exception(e)
            abort(409)
        if page is None:
            abort(404)

        if no_redirect:
            additional_info['redirects_to'] = visited_paths[-1]
        elif len(visited_paths) > 1:
            additional_info['redirected_from'] = visited_paths[:-1]

        result = {'meta': get_page_meta(page), 'text': page.text}
        result.update(additional_info)
        return jsonify(result)

    # Meta listing page or special endpoint.
    meta_page_url = '%s:%s' % (endpoint, path)
    info_page = get_page_or_none(
            meta_page_url,
            fields=['url', 'title', 'text', 'meta'],
            convert_url=False,
            check_perms=CHECK_FOR_READ)

    wiki = get_wiki()
    endpoint_info = wiki.endpoints.get(endpoint)
    if endpoint_info is not None:
        # We have some information about this endpoint...
        if endpoint_info.default and info_page is None:
            # Default page text.
            info_page = get_page_or_404(
                    endpoint_info.default,
                    fields=['url', 'title', 'text', 'meta'],
                    convert_url=False,
                    check_perms=CHECK_FOR_READ)

        if not endpoint_info.query:
            # Not a query-based endpoint (like categories). Let's just
            # return the text.
            result = {
                    'endpoint': endpoint,
                    'meta': get_page_meta(info_page),
                    'text': info_page.text}
            result.update(additional_info)
            return jsonify(result)

    # Get the list of pages to show here.
    value = path.lstrip('/')
    query = {endpoint: [value]}
    pages = wiki.getPages(meta_query=query,
            fields=['url', 'title', 'text', 'meta'])
    tpl_data = {
            'name': endpoint,
            'url': meta_page_url,
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
            'endpoint': endpoint,
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

    result.update(additional_info)
    return jsonify(result)


@app.route('/api/raw/')
def api_read_main_page_raw():
    wiki = get_wiki()
    return api_read_page_raw(wiki.main_page_url.lstrip('/'))


@app.route('/api/raw/<path:url>')
def api_read_page_raw(url):
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ,
            fields=['raw_text', 'meta'])
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
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ,
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
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ,
            fields=['url', 'title', 'links'])
    links = []
    for link in page.links:
        other = get_page_or_none(link, convert_url=False,
                fields=['url', 'title', 'meta'])
        if other is not None and is_page_readable(other):
            links.append(get_page_meta(other))
        else:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'out_links': links}
    return jsonify(result)


@app.route('/api/inlinks/')
def api_get_main_page_incoming_links():
    wiki = get_wiki()
    return api_get_incoming_links(wiki.main_page_url.lstrip('/'))


@app.route('/api/inlinks/<path:url>')
def api_get_incoming_links(url):
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ,
            fields=['url', 'title', 'meta'])
    links = []
    for link in page.getIncomingLinks():
        other = get_page_or_none(link, convert_url=False,
                fields=['url', 'title', 'meta'])
        if other is not None and is_page_readable(other):
            links.append(get_page_meta(other))
        else:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'in_links': links}
    return jsonify(result)

