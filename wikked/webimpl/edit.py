import os.path
import logging
import urllib.parse
from werkzeug.utils import secure_filename
from wikked.auth import PERM_UPLOAD, PERM_WIKIUPLOAD
from wikked.page import Page, PageData
from wikked.formatter import PageFormatter, FormattingContext
from wikked.resolver import PageResolver
from wikked.utils import PageNotFoundError
from wikked.webimpl import (
    get_page_or_raise, get_page_meta, make_page_title,
    UserPermissionError)


logger = logging.getLogger(__name__)


class DummyPage(Page):
    """ A dummy page for previewing in-progress editing.
    """
    def __init__(self, wiki, url, text):
        data = self._loadData(wiki, url, text)
        super(DummyPage, self).__init__(wiki, data)

    def _loadData(self, wiki, url, text):
        data = PageData()
        extension = wiki.fs.default_extension
        data.url = url
        data.path = '__preview__.' + extension
        data.raw_text = text

        ctx = FormattingContext(url)
        f = PageFormatter()
        data.formatted_text = f.formatText(ctx, data.raw_text)
        data.local_meta = ctx.meta
        data.local_links = ctx.out_links

        data.title = (data.local_meta.get('title') or
                      make_page_title(url))
        if isinstance(data.title, list):
            data.title = data.title[0]

        return data


def get_edit_page(wiki, user, url, author=None, custom_data=None):
    page = None
    try:
        page = get_page_or_raise(wiki, url,
                                 check_perms=(user, 'edit'))
    except PageNotFoundError:
        # Only catch errors about the page not existing. Permission
        # errors still go through.
        page = None

    if page is None:
        result = {
                'meta': {
                    'url': urllib.parse.quote(url.encode('utf-8')),
                    'title': make_page_title(url)
                    },
                'text': ''
                }
    else:
        result = {
                'meta': get_page_meta(page, True),
                'text': page.raw_text
                }

    result['commit_meta'] = {
            'author': author,
            'desc': 'Editing ' + result['meta']['title']
            }

    if custom_data:
        result.update(custom_data)

    return result


def do_edit_page(wiki, user, url, text, author=None, message=None):
    try:
        get_page_or_raise(wiki, url,
                          check_perms=(user, 'edit'))
    except PageNotFoundError:
        # Only catch errors about the page not existing. Permission
        # errors still go through.
        pass

    author = author or user
    if author is None:
        raise Exception("No author or user was specified.")

    message = message or 'Edited ' + url
    page_fields = {
            'text': text,
            'author': author,
            'message': message
            }
    wiki.setPage(url, page_fields)


def preview_edited_page(wiki, url, raw_text):
    dummy = DummyPage(wiki, url, raw_text)
    # We can pass `can_use_resolved_meta` since we know we have the only
    # resolver running right now... this will speed things up dramatically.
    resolver = PageResolver(dummy, can_use_resolved_meta=True)
    dummy._setExtendedData(resolver.run())
    return dummy.text


def do_upload_file(wiki, user, reqfile, for_url=None, commit_user=False,
                   submit=True):
    if not reqfile:
        raise Exception("No file was specified.")
    if not reqfile.filename:
        raise Exception("No file name was specified.")

    # Check permissions for the user.
    if for_url:
        for_page = get_page_or_raise(wiki, for_url,
                                     fields=['url', 'local_meta'])
        if not wiki.auth.hasPagePermission(for_page, user, PERM_UPLOAD):
            raise UserPermissionError(
                "You don't have permission to upload files to this page.")
    else:
        if not wiki.auth.hasPermission(user, PERM_WIKIUPLOAD):
            raise UserPermissionError(
                "You don't have permission to upload files.")

    filename = secure_filename(reqfile.filename)

    upload_dir = os.path.join(wiki.root, '_files')
    if for_url:
        fs_info = wiki.fs.findPageInfo(for_url)
        upload_dir, _ = os.path.splitext(fs_info.path)

    path = os.path.join(upload_dir, filename)
    path = os.path.normpath(path)
    if not path.startswith(wiki.root):
        raise Exception("Don't try anything weird, please.")

    # Save to disk.
    os.makedirs(os.path.dirname(path), exist_ok=True)
    reqfile.save(path)

    # Commit the file to the source-control.
    if submit:
        commit_meta = {
            'author': commit_user,
            'message': "Uploaded '%s'." % filename}
        wiki.scm.commit([path], commit_meta)

    if for_url:
        example = './%s' % filename
    else:
        example = filename
    result = {
        'example': example
    }
    return result
