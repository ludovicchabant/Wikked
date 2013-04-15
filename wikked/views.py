import re
import time
import os.path
from flask import render_template, abort, request, g, jsonify
from flask.ext.login import login_user, logout_user, current_user
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import get_formatter_by_name
from web import app, login_manager
from page import Page, PageData
from fs import PageNotFoundError
from formatter import PageFormatter, FormattingContext
import scm


DONT_CHECK = 0
CHECK_FOR_READ = 1
CHECK_FOR_WRITE = 2

COERCE_META = {
    'redirect': Page.title_to_url
    }


class DummyPage(Page):
    def __init__(self, wiki, url, text):
        Page.__init__(self, wiki, url)
        self._text = text

    def _loadCachedData(self):
        extension = self.wiki.config.get('wiki', 'default_extension')
        data = PageData()
        data.path = '__preview__.' + extension
        data.filename = '__preview__'
        data.extension = extension
        data.raw_text = self._text

        ctx = FormattingContext(self.url, slugify=Page.title_to_url)
        f = PageFormatter(self.wiki)
        data.formatted_text = f.formatText(ctx, data.raw_text)
        data.local_meta = ctx.meta
        data.local_links = ctx.out_links

        data.title = Page.url_to_title(self.url)

        return data


def get_page_or_none(url):
    try:
        page = g.wiki.getPage(url)
        return page
    except PageNotFoundError:
        return None


def get_page_or_404(url, check_perms=DONT_CHECK):
    page = get_page_or_none(url)
    if page is not None:
        if check_perms == CHECK_FOR_READ and not is_page_readable(page):
            abort(401)
        elif check_perms == CHECK_FOR_WRITE and not is_page_writable(page):
            abort(401)
        return page
    abort(404)


def is_page_readable(page, user=current_user):
    return page.wiki.auth.isPageReadable(page, user.get_id())


def is_page_writable(page, user=current_user):
    return page.wiki.auth.isPageWritable(page, user.get_id())


def get_page_meta(page, local_only=False):
    if local_only:
        meta = dict(page._getLocalMeta())
    else:
        meta = dict(page.meta)
    meta['title'] = page.title
    meta['url'] = page.url
    for name in COERCE_META:
        if name in meta:
            meta[name] = COERCE_META[name](meta[name])
    return meta


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
                f_info = g.wiki.fs.getPageInfo(f['path'])
                if f_info is None:
                    continue
                page = g.wiki.getPage(f_info.url)
                try:
                    if not is_page_readable(page):
                        continue
                except PageNotFoundError:
                    pass
                rev_data['pages'].append({
                    'url': f_info.url,
                    'action': scm.ACTION_NAMES[f['action']]
                    })
            if len(rev_data['pages']) > 0:
                hist_data.append(rev_data)
        else:
            hist_data.append(rev_data)
    return hist_data


def make_auth_response(data):
    if current_user.is_authenticated():
        data['auth'] = {
                'username': current_user.username,
                'is_admin': current_user.is_admin()
                }
    return jsonify(data)


@app.route('/')
def home():
    return render_template('index.html', cache_bust=('?%d' % time.time()))


@app.route('/read/<path:url>')
def read():
    return render_template('index.html', cache_bust=('?%d' % time.time()))


@app.route('/search')
def search():
    return render_template('index.html', cache_bust=('?%d' % time.time()))


@app.route('/api/list')
def api_list_all_pages():
    return api_list_pages(None)


@app.route('/api/list/<path:url>')
def api_list_pages(url):
    pages = filter(is_page_readable, g.wiki.getPages(url))
    page_metas = [get_page_meta(page) for page in pages]
    result = {'path': url, 'pages': list(page_metas)}
    return make_auth_response(result)


@app.route('/api/read/<path:url>')
def api_read_page(url):
    page = get_page_or_404(url, CHECK_FOR_READ)
    result = {'meta': get_page_meta(page), 'text': page.text}
    return make_auth_response(result)


@app.route('/api/raw/<path:url>')
def api_read_page_raw(url):
    page = get_page_or_404(url, CHECK_FOR_READ)
    result = {'meta': get_page_meta(page), 'text': page.raw_text}
    return make_auth_response(result)


@app.route('/api/revision/<path:url>')
def api_read_page_rev(url):
    rev = request.args.get('rev')
    if rev is None:
        abort(400)
    page = get_page_or_404(url, CHECK_FOR_READ)
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
    page = get_page_or_404(url, CHECK_FOR_READ)
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


@app.route('/api/state/<path:url>')
def api_get_state(url):
    page = get_page_or_404(url, CHECK_FOR_READ)
    state = page.getState()
    return make_auth_response({
        'meta': get_page_meta(page, True),
        'state': scm.STATE_NAMES[state]
        })


@app.route('/api/outlinks/<path:url>')
def api_get_outgoing_links(url):
    page = get_page_or_404(url, CHECK_FOR_READ)
    links = []
    for link in page.links:
        other = get_page_or_none(link)
        if other is not None:
            links.append({
                'url': link,
                'title': other.title
                })
        else:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'out_links': links}
    return make_auth_response(result)


@app.route('/api/inlinks/<path:url>')
def api_get_incoming_links(url):
    page = get_page_or_404(url, CHECK_FOR_READ)
    links = []
    for link in page.getIncomingLinks():
        other = get_page_or_none(link)
        if other is not None and is_page_readable(other):
            links.append({
                'url': link,
                'title': other.title
                })
        else:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'in_links': links}
    return make_auth_response(result)


@app.route('/api/edit/<path:url>', methods=['GET', 'POST'])
def api_edit_page(url):
    if request.method == 'GET':
        page = get_page_or_none(url)
        if page is None:
            result = {
                    'meta': {
                        'url': url,
                        'name': os.path.basename(url),
                        'title': Page.url_to_title(url)
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
        return make_auth_response(result)

    get_page_or_404(url, CHECK_FOR_WRITE)

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

    page_fields = {
            'rev': rev,
            'author': author,
            'message': message
            }
    g.wiki.revertPage(url, page_fields)
    result = {'reverted': 1}
    return make_auth_response(result)


@app.route('/api/rename/<path:url>', methods=['POST'])
def api_rename_page(url):
    pass


@app.route('/api/delete/<path:url>', methods=['POST'])
def api_delete_page(url):
    pass


@app.route('/api/orphans')
def api_special_orphans():
    run_queries = request.args.get('run_queries')

    orphans = []
    pages_with_queries = []
    for page in g.wiki.getPages():
        try:
            if not is_page_readable(page):
                continue
            if len(page.getIncomingLinks()) == 0:
                orphans.append({'path': page.url, 'meta': get_page_meta(page)})
        except Exception as e:
            app.logger.error("Error while inspecting page: %s" % page.url)
            app.logger.error("   %s" % e)
            continue
        if run_queries:
            page_queries = page._getLocalMeta().get('query')
            if page_queries is not None:
                pages_with_queries.append(page)

    if run_queries:
        app.logger.debug("Running queries for %d pages." % len(pages_with_queries))
        links_to_remove = set()
        for page in pages_with_queries:
            links = PageFormatter.parseWikiLinks(page.text)
            links_to_remove |= set(links)
        app.logger.debug( links_to_remove)
        orphans = [o for o in orphans if o['path'] not in links_to_remove]

    result = {'orphans': orphans}
    return make_auth_response(result)


@app.route('/api/history')
def api_site_history():
    history = g.wiki.getHistory()
    hist_data = get_history_data(history, needs_files=True)
    result = {'history': hist_data}
    return make_auth_response(result)


@app.route('/api/history/<path:url>')
def api_page_history(url):
    page = get_page_or_404(url, CHECK_FOR_READ)
    history = page.getHistory()
    hist_data = get_history_data(history)
    result = {'url': url, 'meta': get_page_meta(page), 'history': hist_data}
    return make_auth_response(result)


@app.route('/api/search')
def api_search():
    query = request.args.get('q')

    def is_hit_readable(hit):
        page = get_page_or_none(hit['url'])
        return page is None or is_page_readable(page)
    hits = filter(is_hit_readable, g.wiki.index.search(query))
    result = {'query': query, 'hits': hits}
    return make_auth_response(result)


@app.route('/api/preview', methods=['POST'])
def api_preview():
    url = request.form.get('url')
    text = request.form.get('text')
    dummy = DummyPage(g.wiki, url, text)

    result = {'text': dummy.text}
    return jsonify(result)


@app.route('/api/admin/reindex', methods=['POST'])
def api_admin_reindex():
    if not current_user.is_authenticated() or not current_user.is_admin():
        return login_manager.unauthorized()
    g.wiki.index.reset(g.wiki.getPages())
    result = {'ok': 1}
    return make_auth_response(result)


@app.route('/api/user/login', methods=['POST'])
def api_user_login():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = request.form.get('remember')

    user = g.wiki.auth.getUser(username)
    if user is not None:
        if app.bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=bool(remember))
            result = {'username': username, 'logged_in': 1}
            return make_auth_response(result)
    abort(401)


@app.route('/api/user/is_logged_in')
def api_user_is_logged_in():
    if current_user.is_authenticated():
        result = {'logged_in': True}
        return make_auth_response(result)
    abort(401)


@app.route('/api/user/logout', methods=['POST'])
def api_user_logout():
    logout_user()
    result = {'ok': 1}
    return make_auth_response(result)


@app.route('/api/user/info/<name>')
def api_user_info(name):
    user = g.wiki.auth.getUser(name)
    if user is not None:
        result = {'username': user.username, 'groups': user.groups}
        return make_auth_response(result)
    abort(404)
