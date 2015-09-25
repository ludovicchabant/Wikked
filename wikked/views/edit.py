from flask import redirect, url_for, request, render_template
from flask.ext.login import current_user
from wikked.views import (
        errorhandling_ui2, show_unauthorized_error,
        add_auth_data, add_navigation_data)
from wikked.web import app, get_wiki
from wikked.webimpl import url_from_viewarg
from wikked.webimpl.edit import get_edit_page, do_edit_page


@app.route('/create/')
def create_page_at_root():
    return create_page('/')


@app.route('/create/<path:url>')
def create_page(url):
    wiki = get_wiki()
    if not wiki.auth.hasPermission('writers', current_user.get_id()):
        return show_unauthorized_error(
                error="You're not authorized to create new pages.")

    data = {
            'is_new': True,
            'create_in': url.lstrip('/'),
            'text': '',
            'commit_meta': {
                'author': current_user.get_id() or request.remote_addr,
                'desc': 'Editing ' + url
                },
            'post_back': '/edit'
            }
    add_auth_data(data)
    add_navigation_data(url, data)
    return render_template('edit-page.html', **data)


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

    if request.method == 'GET':
        author = user or request.remote_addr
        custom_data = {
                'post_back': '/edit/' + url.lstrip('/'),
                'preview_url': url}
        data = get_edit_page(wiki, user, url,
                             author=author, custom_data=custom_data)
        add_auth_data(data)
        add_navigation_data(
                url, data,
                read=True, history=True, inlinks=True,
                raw_url='/api/edit/' + url.lstrip('/'))
        return render_template('edit-page.html', **data)

    if request.method == 'POST':
        text = request.form['text']
        author = user or request.form['author'] or request.remote_addr
        message = request.form['message'] or 'Editing ' + url
        do_edit_page(wiki, user, url, text,
                     author=author, message=message)
        return redirect(url_for('read', url=url.lstrip('/')))

