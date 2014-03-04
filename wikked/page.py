import os
import os.path
import re
import logging
from formatter import PageFormatter, FormattingContext


logger = logging.getLogger(__name__)


class PageLoadingError(Exception):
    """ An exception that can get raised if a page can't be loaded.
    """
    pass


class PageData(object):
    def __init__(self):
        self.url = None
        self.path = None
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
    def extension(self):
        if self._data.path is None:
            raise Exception("The 'path' field was not loaded.")
        return os.path.splitext(self._data.path)[1].lstrip('.')

    @property
    def filename(self):
        if self._data.path is None:
            raise Exception("The 'path' field was not loaded.")
        basename = os.path.basename(self._data.filename)
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
    def meta(self):
        return self._data.ext_meta

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

    def getLocalMeta(self):
        return self._data.local_meta

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
        data.raw_text = page_info.content

        # Format the page and get the meta properties.
        ctx = FormattingContext(page_info.url)
        f = PageFormatter(wiki)
        data.formatted_text = f.formatText(ctx, data.raw_text)
        data.local_meta = ctx.meta
        data.local_links = ctx.out_links

        # Add some common meta.
        data.title = data.local_meta.get('title')
        if data.title is None:
            filename = os.path.basename(data.path)
            filename_split = os.path.splitext(filename)
            data.title = re.sub(r'\-', ' ', filename_split[0])

        return data
