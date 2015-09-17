import logging
import urllib.parse
from wikked.page import Page, PageData
from wikked.formatter import PageFormatter, FormattingContext
from wikked.resolver import PageResolver
from wikked.utils import PageNotFoundError, split_page_url
from wikked.webimpl import (
        CHECK_FOR_WRITE,
        get_page_or_raise, get_page_meta)


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


def make_page_title(url):
    endpoint, path = split_page_url(url)
    last_slash = path.rstrip('/').rfind('/')
    if last_slash < 0 or last_slash == 0:
        title = path.lstrip('/')
    else:
        title = path[last_slash + 1:]
    if endpoint:
        return '%s: %s' % (endpoint, title)
    return title


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
            'author': user,
            'message': message
            }
    wiki.setPage(url, page_fields)


def preview_edited_page(wiki, url, raw_text):
    dummy = DummyPage(wiki, url, raw_text)
    resolver = PageResolver(dummy)
    dummy._setExtendedData(resolver.run())
    return dummy.text

