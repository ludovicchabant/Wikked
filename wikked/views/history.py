import urllib.parse
from flask import request, abort, render_template
from flask.ext.login import current_user
from wikked.views import (
        errorhandling_ui, requires_reader_auth,
        add_auth_data, add_navigation_data)
from wikked.web import app, get_wiki
from wikked.webimpl import url_from_viewarg
from wikked.webimpl.history import (
        get_site_history, get_page_history,
        read_page_rev, diff_revs, diff_page_revs)


@app.route('/special/history')
@requires_reader_auth
def site_history():
    wiki = get_wiki()
    user = current_user.get_id()
    after_rev = request.args.get('rev')
    data = get_site_history(wiki, user, after_rev=after_rev)
    last_rev = data['history'][-1]['rev_id']
    data['first_page'] = '/special/history'
    data['next_page'] = '/special/history?rev=%s' % last_rev
    add_auth_data(data)
    add_navigation_data(
            '', data,
            raw_url='/api/site-history')
    return render_template('special-changes.html', **data)


@app.route('/hist/<path:url>')
@errorhandling_ui
def page_history(url):
    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)
    data = get_page_history(wiki, user, url)
    add_auth_data(data)
    add_navigation_data(
            url, data,
            read=True, edit=True, inlinks=True,
            raw_url='/api/history/' + url.lstrip('/'))
    return render_template('history-page.html', **data)


@app.route('/rev/<path:url>')
@errorhandling_ui
def page_rev(url):
    rev = request.args.get('rev')
    if rev is None:
        abort(400)

    raw_url_args = {'rev': rev}

    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)
    data = read_page_rev(wiki, user, url, rev=rev)
    add_auth_data(data)
    add_navigation_data(
            url, data,
            read=True,
            raw_url='/api/revision/%s?%s' % (
                url.lstrip('/'),
                urllib.parse.urlencode(raw_url_args)))
    return render_template('revision-page.html', **data)


@app.route('/diff/<path:url>')
@errorhandling_ui
def diff_page(url):
    rev1 = request.args.get('rev1')
    rev2 = request.args.get('rev2')
    raw = request.args.get('raw')
    if rev1 is None:
        abort(400)

    raw_url_args = {'rev1': rev1}
    if rev2:
        raw_url_args['rev2'] = rev2

    wiki = get_wiki()
    user = current_user.get_id()
    url = url_from_viewarg(url)
    data = diff_page_revs(wiki, user, url,
                          rev1=rev1, rev2=rev2, raw=raw)
    add_auth_data(data)
    add_navigation_data(
            url, data,
            read=True,
            raw_url='/api/diff/%s?%s' % (
                url.lstrip('/'),
                urllib.parse.urlencode(raw_url_args)))
    return render_template('diff-page.html', **data)


@app.route('/diff_rev/<rev>')
@errorhandling_ui
def diff_revision(rev):
    wiki = get_wiki()
    user = current_user.get_id()
    data = diff_revs(wiki, user, rev)
    add_auth_data(data)
    add_navigation_data(
            '', data)
    return render_template('diff-rev.html', **data)

