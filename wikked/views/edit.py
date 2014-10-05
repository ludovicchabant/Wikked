import urllib
from flask import g, abort, request, jsonify
from flask.ext.login import current_user
from wikked.page import Page, PageData
from wikked.formatter import PageFormatter, FormattingContext
from wikked.resolver import PageResolver
from wikked.views import (make_page_title, get_page_or_none,
        is_page_writable, get_page_meta, url_from_viewarg,
        split_url_from_viewarg)
from wikked.web import app, get_wiki


class DummyPage(Page):
    """ A dummy page for previewing in-progress editing.
    """
    def __init__(self, wiki, url, text):
        data = self._loadData(wiki, url, text)
        super(DummyPage, self).__init__(wiki, data)

    def _loadData(self, wiki, url, text):
        data = PageData()
        extension = wiki.fs.default_extension
        data.url = url
        data.path = '__preview__.' + extension
        data.raw_text = text

        ctx = FormattingContext(url)
        f = PageFormatter()
        data.formatted_text = f.formatText(ctx, data.raw_text)
        data.local_meta = ctx.meta
        data.local_links = ctx.out_links

        data.title = (data.local_meta.get('title') or
                make_page_title(url))
        if isinstance(data.title, list):
            data.title = data.title[0]

        return data


def get_edit_page(url, default_title=None, custom_data=None):
    page = get_page_or_none(url, convert_url=False)
    if page is None:
        result = {
                'meta': {
                    'url': urllib.quote(url.encode('utf-8')),
                    'title': default_title or make_page_title(url)
                    },
                'text': ''
                }
    else:
        if not is_page_writable(page):
            abort(401)
        result = {
                'meta': get_page_meta(page, True),
                'text': page.raw_text
                }
    result['commit_meta'] = {
            'author': request.remote_addr,
            'desc': 'Editing ' + result['meta']['title']
            }
    if custom_data:
        result.update(custom_data)
    return jsonify(result)


def do_edit_page(url, default_message):
    page = get_page_or_none(url, convert_url=False)
    if page and not is_page_writable(page):
        app.logger.error("Page '%s' is not writable for user '%s'." % (
            url, current_user.get_id()))
        abort(401)

    if not 'text' in request.form:
        abort(400)
    text = request.form['text']
    author = request.remote_addr
    if 'author' in request.form and len(request.form['author']) > 0:
        author = request.form['author']
    message = 'Edited ' + url
    if 'message' in request.form and len(request.form['message']) > 0:
        message = request.form['message']

    page_fields = {
            'text': text,
            'author': author,
            'message': message
            }
    wiki = get_wiki()
    wiki.setPage(url, page_fields)

    result = {'saved': 1}
    return jsonify(result)


@app.route('/api/edit/', methods=['GET', 'POST'])
def api_edit_main_page():
    wiki = get_wiki()
    return api_edit_page(wiki.main_page_url.lstrip('/'))


@app.route('/api/edit/<path:url>', methods=['GET', 'POST'])
def api_edit_page(url):
    endpoint, path = split_url_from_viewarg(url)

    if request.method == 'GET':
        url = path
        default_title = None
        custom_data = None
        if endpoint is not None:
            url = u'%s:%s' % (endpoint, path)
            default_title = u'%s: %s' % (endpoint, path)
            custom_data = {
                    'meta_query': endpoint,
                    'meta_value': path.lstrip('/')
                    }

        return get_edit_page(
                url,
                default_title=default_title,
                custom_data=custom_data)

    url = path
    default_message = u'Edited ' + url
    if endpoint is not None:
        url = u'%s:%s' % (endpoint, path)
        default_message = u'Edited %s %s' % (endpoint, path.lstrip('/'))
    return do_edit_page(url, default_message)


@app.route('/api/preview', methods=['POST'])
def api_preview():
    url = request.form.get('url')
    url = url_from_viewarg(url)
    text = request.form.get('text')
    wiki = get_wiki()
    dummy = DummyPage(wiki, url, text)

    resolver = PageResolver(dummy)
    dummy._setExtendedData(resolver.run())

    result = {'text': dummy.text}
    return jsonify(result)


@app.route('/api/rename/<path:url>', methods=['POST'])
def api_rename_page(url):
    pass


@app.route('/api/delete/<path:url>', methods=['POST'])
def api_delete_page(url):
    pass


@app.route('/api/validate/newpage', methods=['GET', 'POST'])
def api_validate_newpage():
    path = request.form.get('title')
    if path is None:
        abort(400)
    path = url_from_viewarg(path)
    try:
        # Check that there's no page with that name already, and that
        # the name can be correctly mapped to a filename.
        wiki = get_wiki()
        if wiki.pageExists(path):
            raise Exception("Page '%s' already exists" % path)
        wiki.fs.getPhysicalPagePath(path, make_new=True)
    except Exception:
        return '"This page name is invalid or unavailable"'
    return '"true"'

