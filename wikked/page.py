import os
import os.path
import re
import logging
from .formatter import PageFormatter, FormattingContext


logger = logging.getLogger(__name__)


def get_meta_value(meta, key, first=False):
    value = meta.get(key)
    if value is not None and isinstance(value, list):
        l = len(value)
        if l == 0:
            return None
        if l == 1 or first:
            return value[0]
        return value
    return value


class PageLoadingError(Exception):
    """ An exception that can get raised if a page can't be loaded.
    """
    pass


class PageData(object):
    def __init__(self):
        self.url = None
        self.path = None
        self.cache_time = None
        self.title = None
        self.raw_text = None
        self.formatted_text = None
        self.local_meta = None
        self.local_links = None
        self.text = None
        self.ext_meta = None
        self.ext_links = None


class Page(object):
    """ A wiki page. This is a non-functional class, as it doesn't know where
        to load things from. Use `FileSystemPage` or `DatabasePage` instead.
    """
    def __init__(self, wiki, data):
        self.wiki = wiki
        self._data = data

    @property
    def url(self):
        return self._data.url

    @property
    def path(self):
        return self._data.path

    @property
    def cache_time(self):
        return self._data.cache_time

    @property
    def is_resolved(self):
        return self._data.is_resolved

    @property
    def extension(self):
        if self._data.path is None:
            raise Exception("The 'path' field was not loaded.")
        return os.path.splitext(self._data.path)[1].lstrip('.')

    @property
    def filename(self):
        if self._data.path is None:
            raise Exception("The 'path' field was not loaded.")
        basename = os.path.basename(self._data.path)
        return os.path.splitext(basename)[0]

    @property
    def title(self):
        return self._data.title

    @property
    def raw_text(self):
        return self._data.raw_text

    @property
    def text(self):
        return self._data.text

    @property
    def links(self):
        return self._data.ext_links

    def getIncomingLinks(self):
        return self.wiki.db.getLinksTo(self.url)

    def getHistory(self):
        return self.wiki.scm.getHistory(self.path)

    def getState(self):
        return self.wiki.scm.getState(self.path)

    def getRevision(self, rev):
        return self.wiki.scm.getRevision(self.path, rev)

    def getDiff(self, rev1, rev2):
        return self.wiki.scm.diff(self.path, rev1, rev2)

    def getFormattedText(self):
        return self._data.formatted_text

    def getMeta(self, name=None, first=False):
        if name is None:
            return self._data.ext_meta
        return get_meta_value(self._data.ext_meta, name, first)

    def getLocalMeta(self, name=None, first=False):
        if name is None:
            return self._data.local_meta
        return get_meta_value(self._data.local_meta, name, first)

    def getLocalLinks(self):
        return self._data.local_links

    def _setExtendedData(self, result):
        self._data.text = result.text
        self._data.ext_meta = result.meta
        self._data.ext_links = result.out_links


class FileSystemPage(Page):
    """ A page that can load its properties directly from the file-system.
    """
    def __init__(self, wiki, page_info):
        data = self._loadFromPageInfo(wiki, page_info)
        super(FileSystemPage, self).__init__(wiki, data)

    def _loadFromPageInfo(self, wiki, page_info):
        data = PageData()
        data.url = page_info.url
        data.path = page_info.path
        data.cache_time = None
        data.raw_text = page_info.content

        # Format the page and get the meta properties.
        ctx = FormattingContext(page_info.url)
        f = PageFormatter()
        data.formatted_text = f.formatText(ctx, data.raw_text)
        data.local_meta = ctx.meta
        data.local_links = ctx.out_links

        # Add some common meta.
        data.title = data.local_meta.get('title')
        if data.title is None:
            filename = os.path.basename(data.path)
            filename_split = os.path.splitext(filename)
            data.title = re.sub(r'\-', ' ', filename_split[0])
        elif isinstance(data.title, list):
            data.title = data.title[0]

        return data
