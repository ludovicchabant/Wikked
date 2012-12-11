import time
from flask import (
        Response, 
        render_template, url_for, redirect, abort, request, flash,
        jsonify
        )
from flask.ext.login import login_required, login_user, logout_user, current_user
from wikked import app, wiki
from auth import User
from forms import RegistrationForm, EditPageForm
from fs import PageNotFoundError
import scm


def get_page_or_404(url):
    try:
        page = wiki.getPage(url)
        page._ensureMeta()
        return page
    except PageNotFoundError:
        abort(404)


@app.route('/')
def home():
    return render_template('index.html', cache_bust=('?%d' % time.time()))


@app.route('/api/list')
def api_list_all_pages():
    return list_pages(None)


@app.route('/api/list/<path:url>')
def api_list_pages(url):
    page_names = wiki.getPageNames(url)
    result = { 'pages': list(page_names) }
    return jsonify(result)


@app.route('/api/read/<path:url>')
def api_read_page(url):
    page = get_page_or_404(url)
    result = { 'path': url, 'title': page.title, 'text': page.formatted_text }
    return jsonify(result)


@app.route('/api/raw/<path:url>')
def api_read_page_raw(url):
    page = get_page_or_404(url)
    result = { 'path': url, 'title': page.title, 'text': page.raw_text }
    return jsonify(result)


@app.route('/api/state/<path:url>')
def api_get_state(url):
    try:
        state = wiki.getPageState(url)
    except PageNotFoundError:
        abort(404)
    if state == scm.STATE_NEW:
        result = 'new'
    elif state == scm.STATE_MODIFIED:
        result = 'modified'
    elif state == scm.STATE_COMMITTED:
        result = 'committed'
    return jsonify({ 'path': url, 'state': result })


@app.route('/api/outlinks/<path:url>')
def api_get_outgoing_links(url):
    page = get_page_or_404(url)
    links = page.out_links
    result = { 'path': url, 'out_links': links }
    return jsonify(result)


@app.route('/api/inlinks/<path:url>')
def api_get_incoming_links(url):
    page = get_page_or_404(url)
    links = page.in_links
    result = { 'path': url, 'in_links': links }
    return jsonify(result)


@app.route('/api/edit/<path:url>', methods=['GET', 'PUT', 'POST'])
def api_edit_page(url):
    if request.method == 'GET':
        return api_read_page_raw(url)

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
    history = wiki.getPageHistory(url)
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
    result = { 'url': url, 'history': hist_data }
    return jsonify(result)

