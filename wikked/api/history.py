from flask import request, abort, jsonify
from flask.ext.login import current_user
from wikked.web import app, get_wiki
from wikked.webimpl import url_from_viewarg
from wikked.webimpl.history import (
        get_site_history, get_page_history,
        read_page_rev, diff_page_revs)


@app.route('/api/site-history')
def api_site_history():
    wiki = get_wiki()
    user = current_user.get_id()
    after_rev = request.args.get('rev')
    result = get_site_history(wiki, user, after_rev=after_rev)
    return jsonify(result)


@app.route('/api/history/')
def api_main_page_history():
    wiki = get_wiki()
    return api_page_history(wiki.main_page_url.lstrip('/'))


@app.route('/api/history/<path:url>')
def api_page_history(url):
    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)
    result = get_page_history(wiki, user, url)
    return jsonify(result)


@app.route('/api/revision/<path:url>')
def api_read_page_rev(url):
    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)
    rev = request.args.get('rev')
    if rev is None:
        abort(400)
    result = read_page_rev(wiki, user, url, rev=rev)
    return jsonify(result)


@app.route('/api/diff/<path:url>')
def api_diff_page(url):
    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)
    rev1 = request.args.get('rev1')
    rev2 = request.args.get('rev2')
    raw = request.args.get('raw')
    if rev1 is None:
        abort(400)
    result = diff_page_revs(wiki, user, url,
                            rev1=rev1, rev2=rev2, raw=raw)
    return jsonify(result)


@app.route('/api/revert/<path:url>', methods=['POST'])
def api_revert_page(url):
    # TODO: only users with write access can revert.
    if 'rev' not in request.form:
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
    wiki = get_wiki()
    wiki.revertPage(url, page_fields)
    result = {'reverted': 1}
    return jsonify(result)

