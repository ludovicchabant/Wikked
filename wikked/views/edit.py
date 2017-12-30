from flask import abort, redirect, url_for, request, render_template
from flask.ext.login import current_user
from wikked.views import (
        errorhandling_ui2, show_unauthorized_error,
        add_auth_data, add_navigation_data)
from wikked.web import app, get_wiki
from wikked.webimpl import url_from_viewarg
from wikked.webimpl.edit import (
    get_edit_page, do_edit_page, preview_edited_page, do_upload_file)


@app.route('/create/', methods=['GET'])
def create_page_at_root():
    return create_page('/')


@app.route('/create/<path:url_folder>')
def create_page(url_folder):
    wiki = get_wiki()
    if not wiki.auth.hasPermission('writers', current_user.get_id()):
        return show_unauthorized_error(
                error="You're not authorized to create new pages.")

    title_hint = ((url_folder or '') + '/New Page').lstrip('/')
    data = {
            'is_new': True,
            'title_hint': title_hint,
            'text': '',
            'commit_meta': {
                'author': current_user.get_id() or request.remote_addr,
                'desc': 'Creating new page',
                },
            'post_back': url_for('create_page_postback')
            }
    add_auth_data(data)
    add_navigation_data(None, data, new_page=False)
    return render_template('edit-page.html', **data)


@app.route('/create', methods=['POST'])
def create_page_postback():
    wiki = get_wiki()
    if not wiki.auth.hasPermission('writers', current_user.get_id()):
        return show_unauthorized_error(
                error="You're not authorized to create new pages.")

    url = request.form['title']
    return edit_page(url)


@app.route('/edit', methods=['POST'])
@errorhandling_ui2('error-unauthorized-edit.html')
def edit_new_page():
    url = request.form['title']
    return edit_page(url)


@app.route('/edit/<path:url>', methods=['GET', 'POST'])
@errorhandling_ui2('error-unauthorized-edit.html')
def edit_page(url):
    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)

    if request.method == 'GET' or (
            request.method == 'POST' and 'do-back-to-edit' in request.form):
        author = user or request.remote_addr
        custom_data = {
                'post_back': url_for('edit_page', url=url.lstrip('/')),
                'preview_url': url}
        data = get_edit_page(wiki, user, url,
                             author=author, custom_data=custom_data)
        if 'previewed_text' in request.form:
            data['text'] = request.form['previewed_text']
        add_auth_data(data)
        add_navigation_data(
                url, data,
                read=True, history=True, inlinks=True, upload=True,
                raw_url=url_for('api_read_page', url=url.lstrip('/')))
        return render_template('edit-page.html', **data)

    if request.method == 'POST':
        text = request.form['text']
        author = user or request.form['author'] or request.remote_addr
        message = request.form['message'] or 'Editing ' + url

        if 'do-preview' in request.form:
            data = get_edit_page(wiki, user, url, author=author)
            preview = preview_edited_page(wiki, url, text)
            data['raw_text'] = text
            data['text'] = preview
            data['post_back'] = url_for('edit_page', url=url.lstrip('/'))
            add_auth_data(data)
            add_navigation_data(url, data, new_page=False)
            return render_template('preview-page.html', **data)

        elif 'do-save' in request.form:
            do_edit_page(wiki, user, url, text,
                         author=author, message=message)
            return redirect(url_for('read', url=url.lstrip('/')))

        else:
            abort(400)


@app.route('/upload', methods=['GET', 'POST'])
@errorhandling_ui2('error-unauthorized-upload.html')
def upload_file():
    p = request.args.get('p')
    data = {
        'post_back': url_for('upload_file', p=p),
        'for_page': p
    }
    add_auth_data(data)
    add_navigation_data(p, data)

    if request.method == 'GET':
        return render_template('upload-file.html', **data)

    if request.method == 'POST':
        wiki = get_wiki()
        user = current_user.get_id() or request.remote_addr

        for_url = None
        is_page_specific = (request.form.get('is_page_specific') == 'true')
        if is_page_specific:
            for_url = p

        res = do_upload_file(
            wiki, user, request.files.get('file'),
            for_url=for_url)

        data['success'] = {
            'example': res['example'],
            'is_page_specific': is_page_specific}

        return render_template('upload-file.html', **data)
