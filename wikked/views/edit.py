import urllib
from flask import g, abort, request, jsonify
from flask.ext.login import current_user
from wikked.page import Page, PageData
from wikked.formatter import PageFormatter, FormattingContext
from wikked.views import (make_page_title, make_auth_response, get_page_or_none,
        is_page_writable, get_page_meta, url_from_viewarg,
        split_url_from_viewarg)
from wikked.web import app


class DummyPage(Page):
    """ A dummy page for previewing in-progress editing.
    """
    def __init__(self, wiki, url, text):
        Page.__init__(self, wiki, url)
        self._text = text

    def _loadData(self):
        extension = self.wiki.config.get('wiki', 'default_extension')
        data = PageData()
        data.path = '__preview__.' + extension
        data.filename = '__preview__'
        data.extension = extension
        data.raw_text = self._text

        ctx = FormattingContext(self.url)
        f = PageFormatter(self.wiki)
        data.formatted_text = f.formatText(ctx, data.raw_text)
        data.local_meta = ctx.meta
        data.local_links = ctx.out_links

        data.title = make_page_title(self.url)

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
    return make_auth_response(result)


def do_edit_page(url, default_message):
    page = get_page_or_none(url, convert_url=False)
    if page and not is_page_writable(page):
        app.logger.error("Page '%s' is not writable for user '%s'." % (url, current_user.get_id()))
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
    g.wiki.setPage(url, page_fields)

    result = {'saved': 1}
    return make_auth_response(result)


@app.route('/api/edit/', methods=['GET', 'POST'])
def api_edit_main_page():
    return api_edit_page(g.wiki.main_page_url.lstrip('/'))


@app.route('/api/edit/<path:url>', methods=['GET', 'POST'])
def api_edit_page(url):
    endpoint, value, path = split_url_from_viewarg(url)

    if request.method == 'GET':
        url = path
        default_title = None
        custom_data = None
        if endpoint is not None:
            url = u'%s:%s' % (endpoint, path)
            default_title = u'%s: %s' % (endpoint, value)
            custom_data = {
                    'meta_query': endpoint,
                    'meta_value': value
                    }

        return get_edit_page(
                url,
                default_title=default_title,
                custom_data=custom_data)

    url = path
    default_message = u'Edited ' + url
    if endpoint is not None:
        url = u'%s:%s' % (endpoint, path)
        default_message = u'Edited %s %s' % (endpoint, value)
    return do_edit_page(url, default_message)


@app.route('/api/preview', methods=['POST'])
def api_preview():
    url = request.form.get('url')
    url = url_from_viewarg(url)
    text = request.form.get('text')
    dummy = DummyPage(g.wiki, url, text)

    result = {'text': dummy.text}
    return jsonify(result)


@app.route('/api/rename/<path:url>', methods=['POST'])
def api_rename_page(url):
    pass


@app.route('/api/delete/<path:url>', methods=['POST'])
def api_delete_page(url):
    pass

