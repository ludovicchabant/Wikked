import time
from flask import (
        Response, 
        render_template, url_for, redirect, abort, request, flash,
        jsonify
        )
from flask.ext.login import login_required, login_user, logout_user, current_user
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import get_formatter_by_name
from wikked import app, wiki
from auth import User
from forms import RegistrationForm, EditPageForm
from fs import PageNotFoundError
import scm


def get_page_or_none(url):
    try:
        page = wiki.getPage(url)
        page._ensureMeta()
        return page
    except PageNotFoundError:
        return None

def get_page_or_404(url):
    page = get_page_or_none(url)
    if page is not None:
        return page
    abort(404)


@app.route('/')
def home():
    return render_template('index.html', cache_bust=('?%d' % time.time()))


@app.route('/api/list')
def api_list_all_pages():
    return list_pages(None)


@app.route('/api/list/<path:url>')
def api_list_pages(url):
    page_metas = [page.all_meta for page in wiki.getPages(url)]
    result = { 'path': url, 'pages': list(page_metas) }
    return jsonify(result)


@app.route('/api/read/<path:url>')
def api_read_page(url):
    page = get_page_or_404(url)
    result = { 'path': url, 'meta': page.all_meta, 'text': page.formatted_text }
    return jsonify(result)


@app.route('/api/raw/<path:url>')
def api_read_page_raw(url):
    page = get_page_or_404(url)
    result = { 'path': url, 'meta': page.all_meta, 'text': page.raw_text }
    return jsonify(result)


@app.route('/api/revision/<path:url>/<rev>')
def api_read_page_rev(url, rev):
    page = get_page_or_404(url)
    page_rev = page.getRevision(rev)
    meta = dict(page.all_meta, rev=rev)
    result = { 'path': url, 'meta': meta, 'text': page_rev }
    return jsonify(result)


@app.route('/api/diff/<path:url>/<rev>')
def api_diff_page_change(url, rev):
    return api_diff_page_revs(url, rev, None)


@app.route('/api/diff/<path:url>/<rev1>/<rev2>')
def api_diff_page_revs(url, rev1, rev2):
    page = get_page_or_404(url)
    diff = page.getDiff(rev1, rev2)
    if 'raw' not in request.args:
        lexer = get_lexer_by_name('diff')
        formatter = get_formatter_by_name('html')
        diff = highlight(diff, lexer, formatter)
    if rev2 is None:
        meta = dict(page.all_meta, change=rev)
    else:
        meta = dict(page.all_meta, rev1=rev1, rev2=rev2)
    result = { 'path': url, 'meta': meta, 'diff': diff }
    return jsonify(result)


@app.route('/api/state/<path:url>')
def api_get_state(url):
    page = get_page_or_404(url)
    state = page.getState()
    if state == scm.STATE_NEW:
        result = 'new'
    elif state == scm.STATE_MODIFIED:
        result = 'modified'
    elif state == scm.STATE_COMMITTED:
        result = 'committed'
    return jsonify({ 'path': url, 'meta': page.all_meta, 'state': result })


@app.route('/api/outlinks/<path:url>')
def api_get_outgoing_links(url):
    page = get_page_or_404(url)
    links = []
    for link in page.out_links:
        other = get_page_or_none(link)
        if other is not None:
            links.append({
                'url': link,
                'title': other.title
                })
        else:
            links.append({ 'url': link, 'missing': True })

    result = { 'path': url, 'meta': page.all_meta, 'out_links': links }
    return jsonify(result)


@app.route('/api/inlinks/<path:url>')
def api_get_incoming_links(url):
    page = get_page_or_404(url)
    links = []
    for link in page.in_links:
        other = get_page_or_none(link)
        if other is not None:
            links.append({
                'url': link,
                'meta': other.all_meta
                })
        else:
            links.append({ 'url': link, 'missing': True })

    result = { 'path': url, 'meta': page.all_meta, 'in_links': links }
    return jsonify(result)


@app.route('/api/edit/<path:url>', methods=['GET', 'PUT', 'POST'])
def api_edit_page(url):
    if request.method == 'GET':
        page = get_page_or_404(url)
        result = { 
                'path': url, 
                'meta': page.all_meta, 
                'commit_meta': {
                    'author': request.remote_addr,
                    'desc': 'Editing ' + page.title
                    },
                'text': page.raw_text
                }
        return jsonify(result)

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
    wiki.setPage(url, page_fields)
    result = { 'path': url, 'saved': 1 }
    return jsonify(result)


@app.route('/api/rename/<path:url>', methods=['POST'])
def api_rename_page(url):
    pass


@app.route('/api/delete/<path:url>', methods=['POST'])
def api_delete_page(url):
    pass


@app.route('/api/history')
def api_site_history():
    pass


@app.route('/api/history/<path:url>')
def api_page_history(url):
    page = get_page_or_404(url)
    history = page.getHistory()
    hist_data = []
    for i, rev in enumerate(reversed(history)):
        hist_data.append({
            'index': i + 1,
            'rev_id': rev.rev_id,
            'rev_hash': rev.rev_hash,
            'author': rev.author,
            'timestamp': rev.timestamp,
            'description': rev.description
            })
    result = { 'url': url, 'meta': page.all_meta, 'history': hist_data }
    return jsonify(result)

