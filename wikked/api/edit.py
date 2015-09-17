from flask import abort, request, jsonify
from flask.ext.login import current_user
from wikked.web import app, get_wiki
from wikked.webimpl import url_from_viewarg, split_url_from_viewarg
from wikked.webimpl.edit import (
        get_edit_page, do_edit_page, preview_edited_page)


@app.route('/api/edit/<path:url>', methods=['GET', 'POST'])
def api_edit_page(url):
    wiki = get_wiki()
    user = current_user.get_id()
    endpoint, path = split_url_from_viewarg(url)

    if request.method == 'GET':
        url = path
        custom_data = None
        if endpoint is not None:
            url = '%s:%s' % (endpoint, path)
            custom_data = {
                    'meta_query': endpoint,
                    'meta_value': path.lstrip('/')
                    }

        data = get_edit_page(
                wiki, user, url,
                custom_data=custom_data)
        return jsonify(data)

    if request.method == 'POST':
        url = path
        if endpoint is not None:
            url = '%s:%s' % (endpoint, path)

        author = user or request.form.get('author')
        if not author:
            abort(400)

        message = request.form.get('message')
        if not message:
            abort(400)

        do_edit_page(wiki, user, url, author, message)
        return jsonify({'edited': True})


@app.route('/api/preview', methods=['POST'])
def api_preview():
    url = request.form.get('url')
    if url == '' or not url[0] == '/':
        abort(400)

    text = request.form.get('text')
    wiki = get_wiki()
    preview = preview_edited_page(wiki, url, text)
    result = {'text': preview}
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

