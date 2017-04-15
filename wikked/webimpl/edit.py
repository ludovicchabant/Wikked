import os.path
import logging
import urllib.parse
from werkzeug.utils import secure_filename
from wikked.page import Page, PageData
from wikked.formatter import PageFormatter, FormattingContext
from wikked.resolver import PageResolver
from wikked.utils import PageNotFoundError
from wikked.webimpl import (
        CHECK_FOR_WRITE,
        get_page_or_raise, get_page_meta, make_page_title)


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
                                 check_perms=(user, CHECK_FOR_WRITE))
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
                          check_perms=(user, CHECK_FOR_WRITE))
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
    resolver = PageResolver(dummy)
    dummy._setExtendedData(resolver.run())
    return dummy.text


def do_upload_file(wiki, user, reqfile, for_url=None, submit=True):
    if not reqfile:
        raise Exception("No file was specified.")
    if not reqfile.filename:
        raise Exception("No file name was specified.")

    # TODO: check permissions for the user.

    filename = secure_filename(reqfile.filename)

    files_dir = os.path.join(wiki.root, '_files')
    upload_dir = files_dir
    if for_url:
        upload_dir = os.path.join(wiki.root, for_url)

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
            'author': user,
            'message': "Uploaded '%s'." % filename}
        wiki.scm.commit([path], commit_meta)

    if for_url:
        example = './%s' % filename
    else:
        example = os.path.relpath(path, files_dir)
    result = {
        'example': example
    }
    return result
