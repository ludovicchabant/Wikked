import os.path
import datetime
from pygments import highlight
from pygments.formatters import get_formatter_by_name
from pygments.lexers import get_lexer_by_name
from wikked.scm.base import ACTION_NAMES, ACTION_ADD, ACTION_EDIT
from wikked.webimpl import get_page_meta, get_page_or_raise


def get_history_data(wiki, user, history, needs_files=False):
    hist_data = []
    for i, rev in enumerate(history):
        rev_data = {
            'index': i + 1,
            'rev_id': rev.rev_id,
            'rev_name': rev.rev_name,
            'author': rev.author.name,
            'timestamp': rev.timestamp,
            'description': rev.description
            }
        dt = datetime.datetime.fromtimestamp(rev.timestamp)
        rev_data['datetime'] = dt.strftime('%x %X')
        if needs_files:
            rev_data['pages'] = []
            for f in rev.files:
                path = os.path.join(wiki.root, f.path)
                page_info = wiki.fs.getPageInfo(path)
                action_name = ACTION_NAMES[f.action]
                if page_info is not None:
                    rev_data['pages'].append({
                        'url': page_info.url,
                        'is_add_or_edit': (f.action == ACTION_ADD or
                                           f.action == ACTION_EDIT),
                        'action': action_name})
                else:
                    rev_data['pages'].append({
                        'path': f.path,
                        'action': action_name})
            rev_data['num_pages'] = len(rev_data['pages'])
            if len(rev_data['pages']) > 0:
                hist_data.append(rev_data)
        else:
            hist_data.append(rev_data)
    return hist_data


def get_site_history(wiki, user, after_rev=None):
    history = wiki.getHistory(limit=10, after_rev=after_rev)
    hist_data = get_history_data(wiki, user, history, needs_files=True)
    result = {'history': hist_data}
    return result


def get_page_history(wiki, user, url):
    page = get_page_or_raise(wiki, url, check_perms=(user, 'read,history'))
    history = page.getHistory()
    hist_data = get_history_data(wiki, user, history)
    result = {'url': url, 'meta': get_page_meta(page), 'history': hist_data}
    return result


def read_page_rev(wiki, user, url, rev):
    page = get_page_or_raise(wiki, url, check_perms=(user, 'read,history'))
    page_rev = page.getRevision(rev)
    meta = dict(get_page_meta(page, True), rev=rev)
    result = {'meta': meta, 'text': page_rev}
    return result


def diff_page_revs(wiki, user, url, rev1, rev2=None, raw=False):
    page = get_page_or_raise(wiki, url, check_perms=(user, 'read,history'))
    diff = page.getDiff(rev1, rev2)
    if not raw:
        lexer = get_lexer_by_name('diff')
        formatter = get_formatter_by_name('html')
        diff = highlight(diff, lexer, formatter)
    if rev2 is None:
        meta = dict(get_page_meta(page, True), change=rev1)
    else:
        meta = dict(get_page_meta(page, True), rev1=rev1, rev2=rev2)
    result = {'meta': meta, 'diff': diff}
    return result


def diff_revs(wiki, user, rev, raw=False):
    diff = wiki.scm.diff(path=None, rev1=rev, rev2=None)
    if not raw:
        lexer = get_lexer_by_name('diff')
        formatter = get_formatter_by_name('html')
        diff = highlight(diff, lexer, formatter)
    return {'diff': diff, 'disp_rev': rev}


def revert_page(wiki, user, url, rev, message=None):
    message = message or 'Reverted %s to revision %s' % (url, rev)
    page_fields = {
            'rev': rev,
            'author': user,
            'message': message
            }
    wiki.revertPage(url, page_fields)
