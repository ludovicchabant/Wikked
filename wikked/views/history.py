import os.path
from flask import g, request, abort
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import get_formatter_by_name
from wikked.page import PageLoadingError
from wikked.scm.base import ACTION_NAMES
from wikked.utils import PageNotFoundError
from wikked.views import (is_page_readable, get_page_meta, get_page_or_404,
        make_auth_response, url_from_viewarg,
        CHECK_FOR_READ)
from wikked.web import app


def get_history_data(history, needs_files=False):
    hist_data = []
    for i, rev in enumerate(reversed(history)):
        rev_data = {
            'index': i + 1,
            'rev_id': rev.rev_id,
            'rev_name': rev.rev_name,
            'author': rev.author,
            'timestamp': rev.timestamp,
            'description': rev.description
            }
        if needs_files:
            rev_data['pages'] = []
            for f in rev.files:
                url = None
                path = os.path.join(g.wiki.root, f['path'])
                try:
                    page = g.wiki.db.getPage(path=path)
                    # Hide pages that the user can't see.
                    if not is_page_readable(page):
                        continue
                    url = page.url
                except PageNotFoundError:
                    pass
                except PageLoadingError:
                    pass
                if not url:
                    url = os.path.splitext(f['path'])[0]
                rev_data['pages'].append({
                    'url': url,
                    'action': ACTION_NAMES[f['action']]
                    })
            rev_data['num_pages'] = len(rev_data['pages'])
            rev_data['make_collapsable'] = len(rev_data['pages']) > 1
            if len(rev_data['pages']) > 0:
                hist_data.append(rev_data)
        else:
            hist_data.append(rev_data)
    return hist_data


@app.route('/api/history')
def api_site_history():
    limit = request.args.get('l')
    if not limit:
        limit = 10
    else:
        limit = int(limit)

    history = g.wiki.getHistory(limit=limit)
    hist_data = get_history_data(history, needs_files=True)
    result = {'history': hist_data}
    return make_auth_response(result)


@app.route('/api/history/<path:url>')
def api_page_history(url):
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ)
    history = page.getHistory()
    hist_data = get_history_data(history)
    result = {'url': url, 'meta': get_page_meta(page), 'history': hist_data}
    return make_auth_response(result)


@app.route('/api/revision/<path:url>')
def api_read_page_rev(url):
    rev = request.args.get('rev')
    if rev is None:
        abort(400)
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ)
    page_rev = page.getRevision(rev)
    meta = dict(get_page_meta(page, True), rev=rev)
    result = {'meta': meta, 'text': page_rev}
    return make_auth_response(result)


@app.route('/api/diff/<path:url>')
def api_diff_page(url):
    rev1 = request.args.get('rev1')
    rev2 = request.args.get('rev2')
    if rev1 is None:
        abort(400)
    page = get_page_or_404(url, check_perms=CHECK_FOR_READ)
    diff = page.getDiff(rev1, rev2)
    if 'raw' not in request.args:
        lexer = get_lexer_by_name('diff')
        formatter = get_formatter_by_name('html')
        diff = highlight(diff, lexer, formatter)
    if rev2 is None:
        meta = dict(get_page_meta(page, True), change=rev1)
    else:
        meta = dict(get_page_meta(page, True), rev1=rev1, rev2=rev2)
    result = {'meta': meta, 'diff': diff}
    return make_auth_response(result)


@app.route('/api/revert/<path:url>', methods=['POST'])
def api_revert_page(url):
    if not 'rev' in request.form:
        abort(400)
    rev = request.form['rev']
    author = request.remote_addr
    if 'author' in request.form and len(request.form['author']) > 0:
        author = request.form['author']
    message = 'Reverted %s to revision %s' % (url, rev)
    if 'message' in request.form and len(request.form['message']) > 0:
        message = request.form['message']

    url = url_from_viewarg(url)
    page_fields = {
            'rev': rev,
            'author': author,
            'message': message
            }
    g.wiki.revertPage(url, page_fields)
    result = {'reverted': 1}
    return make_auth_response(result)

