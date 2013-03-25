import os
import os.path
import re
import datetime
import unicodedata
import pystache
from formatter import PageFormatter, FormattingContext
from resolver import PageResolver, CircularIncludeError


class PageData(object):
    def __init__(self):
        self.path = None
        self.title = None
        self.raw_text = None
        self.formatted_text = None
        self.text = None
        self.local_meta = {}
        self.local_links = []
        self.ext_meta = {}
        self.ext_links = []
        self.has_extended_data = False


class Page(object):
    """ A wiki page.
    """
    def __init__(self, wiki, url):
        self.wiki = wiki
        self.url = url
        self._data = None

    @property
    def path(self):
        self._ensureData()
        return self._data.path

    @property
    def title(self):
        self._ensureData()
        return self._data.title

    @property
    def raw_text(self):
        self._ensureData()
        return self._data.raw_text

    @property
    def text(self):
        self._ensureExtendedData()
        return self._data.text

    @property
    def meta(self):
        self._ensureExtendedData()
        return self._data.ext_meta

    @property
    def links(self):
        self._ensureExtendedData()
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

    def _getFormattedText(self):
        self._ensureData()
        return self._data.formatted_text

    def _getLocalMeta(self):
        self._ensureData()
        return self._data.local_meta

    def _getLocalLinks(self):
        self._ensureData()
        return self._data.local_links

    def _ensureData(self):
        if self._data is not None:
            return

        self._data = self._loadCachedData()
        if self._data is not None:
            return

        self._data = self._loadOriginalData()
        self._saveCachedData(self._data)

    def _loadCachedData(self):
        return None

    def _saveCachedData(self, meta):
        pass

    def _loadOriginalData(self):
        data = PageData()

        # Get info from the file-system.
        page_info = self.wiki.fs.getPage(self.url)
        data.path = page_info.path
        data.raw_text = page_info.content

        # Format the page and get the meta properties.
        filename = os.path.basename(data.path)
        filename_split = os.path.splitext(filename)
        extension = filename_split[1].lstrip('.')
        ctx = FormattingContext(self.url, extension, slugify=Page.title_to_url)
        f = PageFormatter(self.wiki)
        data.formatted_text = f.formatText(ctx, data.raw_text)
        data.local_meta = ctx.meta
        data.local_links = ctx.out_links

        # Add some common meta.
        data.title = re.sub(r'\-', ' ', filename_split[0])
        if 'title' in data.local_meta:
            data.title = data.local_meta['title'][0]

        return data

    def _ensureExtendedData(self):
        if self._data is not None and self._data.has_extended_data:
            return

        self._ensureData()
        try:
            r = PageResolver(self)
            out = r.run()
            self._data.text = out.text
            self._data.ext_meta = out.meta
            self._data.ext_links = out.out_links
        except CircularIncludeError as cie:
            template_path = os.path.join(
                    os.path.dirname(__file__),
                    'templates',
                    'circular_include_error.html'
                    )
            with open(template_path, 'r') as f:
                template = pystache.compile(f.read())
            self._data.text = template({
                    'message': str(cie),
                    'url_trail': cie.url_trail
                    })

    @staticmethod
    def title_to_url(title):
        # Remove diacritics (accents, etc.) and replace them with ASCII
        # equivelent.
        ansi_title = ''.join((c for c in
            unicodedata.normalize('NFD', unicode(title))
            if unicodedata.category(c) != 'Mn'))
        # Now replace spaces and punctuation with a hyphen.
        return re.sub(r'[^A-Za-z0-9_\.\-\(\)]+', '-', ansi_title.lower())

    @staticmethod
    def url_to_title(url):
        def upperChar(m):
            return m.group(0).upper()
        return re.sub(r'^.|\s\S', upperChar, url.lower().replace('-', ' '))

    @staticmethod
    def factory(wiki, url):
        return Page(wiki, url)


class DatabasePage(Page):
    """ A page that can load its properties from a
        database.
    """
    def __init__(self, wiki, url):
        Page.__init__(self, wiki, url)
        if getattr(wiki, 'db', None) is None:
            raise Exception("The wiki doesn't have a database.")
        self.auto_update = wiki.config.get('wiki', 'auto_update')

    def _loadCachedData(self):
        if self.wiki.db is None:
            return None
        db_page = self.wiki.db.getPage(self.url)
        if db_page is None:
            return None
        if self.auto_update:
            path_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(db_page.path))
            if path_time >= db_page.time:
                return None
        data = PageData()
        data.path = db_page.path
        data.title = db_page.title
        data.raw_text = db_page.raw_text
        data.formatted_text = db_page.formatted_text
        data.local_meta = db_page.meta
        data.local_links = db_page.links
        return data

    def _saveCachedData(self, meta):
        if self.wiki.db is not None:
            self.wiki.logger.debug(
                "Updated database cache for page '%s'." % self.url)
            self.wiki.db.update([self])

    @staticmethod
    def factory(wiki, url):
        return DatabasePage(wiki, url)
