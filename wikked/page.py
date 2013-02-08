import os
import os.path
import re
import datetime
import unicodedata
import pystache
from formatter import PageFormatter, FormattingContext, PageResolver, CircularIncludeError


class Page(object):
    """ A wiki page.
    """
    def __init__(self, wiki, url):
        self.wiki = wiki
        self.url = url
        self._meta = None
        self._ext_meta = None

    @property
    def path(self):
        self._ensureMeta()
        return self._meta['path']

    @property
    def title(self):
        self._ensureMeta()
        return self._meta['title']

    @property
    def raw_text(self):
        self._ensureMeta()
        return self._meta['content']

    @property
    def formatted_text(self):
        self._ensureMeta()
        return self._meta['formatted']

    @property
    def text(self):
        self._ensureExtendedMeta()
        return self._ext_meta['text']

    @property
    def local_meta(self):
        self._ensureMeta()
        return self._meta['meta']

    @property
    def local_links(self):
        self._ensureMeta()
        return self._meta['links']

    @property
    def all_meta(self):
        self._ensureExtendedMeta()
        return self._ext_meta['meta']

    @property
    def all_links(self):
        self._ensureExtendedMeta()
        return self._ext_meta['links']

    @property
    def in_links(self):
        return self.wiki.db.getLinksTo(self.url)

    def getHistory(self):
        return self.wiki.scm.getHistory(self.path)

    def getState(self):
        return self.wiki.scm.getState(self.path)

    def getRevision(self, rev):
        return self.wiki.scm.getRevision(self.path, rev)

    def getDiff(self, rev1, rev2):
        return self.wiki.scm.diff(self.path, rev1, rev2)

    def _ensureMeta(self):
        if self._meta is not None:
            return

        self._meta = self._loadCachedMeta()
        if self._meta is not None:
            return

        self._meta = self._loadOriginalMeta()
        self._saveCachedMeta(self._meta)

    def _loadCachedMeta(self):
        return None

    def _saveCachedMeta(self, meta):
        pass

    def _loadOriginalMeta(self):
        # Get info from the file-system.
        meta = self.wiki.fs.getPage(self.url)

        # Format the page and get the meta properties.
        filename = os.path.basename(meta['path'])
        filename_split = os.path.splitext(filename)
        extension = filename_split[1].lstrip('.')
        ctx = FormattingContext(self.url, extension, slugify=Page.title_to_url)
        f = PageFormatter(self.wiki)
        meta['formatted'] = f.formatText(ctx, meta['content'])
        meta['meta'] = ctx.meta
        meta['links'] = ctx.out_links

        # Add some common meta.
        meta['title'] = re.sub(r'\-', ' ', filename_split[0])
        if 'title' in meta['meta']:
            meta['title'] = meta['meta']['title']

        return meta

    def _ensureExtendedMeta(self):
        if self._ext_meta is not None:
            return

        try:
            r = PageResolver(self)
            out = r.run()
            self._ext_meta = {}
            self._ext_meta['text'] = out.text
            self._ext_meta['meta'] = out.meta
            self._ext_meta['links'] = out.out_links
        except CircularIncludeError as cie:
            template_path = os.path.join(
                    os.path.dirname(__file__),
                    'templates',
                    'circular_include_error.html'
                    )
            with open(template_path, 'r') as f:
                template = pystache.compile(f.read())
            self._ext_meta = {
                    'text': template({
                        'message': str(cie),
                        'url_trail': cie.url_trail
                        }),
                    'meta': {},
                    'links': []
                    }

    @staticmethod
    def title_to_url(title):
        # Remove diacritics (accents, etc.) and replace them with ASCII
        # equivelent.
        ansi_title = ''.join((c for c in
            unicodedata.normalize('NFD', unicode(title))
            if unicodedata.category(c) != 'Mn'))
        # Now replace spaces and punctuation with a hyphen.
        return re.sub(r'[^A-Za-z0-9_\.\-\(\)/]+', '-', ansi_title.lower())

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

    def _loadCachedMeta(self):
        if self.wiki.db is None:
            return None
        db_page = self.wiki.db.getPage(self.url)
        if db_page is None:
            return None
        if self.auto_update:
            path_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(db_page['path']))
            if path_time >= db_page['time']:
                return None
        meta = {
                'url': self.url,
                'path': db_page['path'],
                'content': db_page['content'],
                'formatted': db_page['formatted'],
                'meta': db_page['meta'],
                'title': db_page['title'],
                'links': db_page['links']
                }
        return meta

    def _saveCachedMeta(self, meta):
        if self.wiki.db is not None:
            self.wiki.logger.debug(
                "Updated database cache for page '%s'." % self.url)
            self.wiki.db.update([self])

    @staticmethod
    def factory(wiki, url):
        return DatabasePage(wiki, url)
