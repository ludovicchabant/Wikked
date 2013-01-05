import os
import os.path
import re
import time
import logging
import itertools
from ConfigParser import SafeConfigParser
import markdown
from fs import FileSystem
from cache import Cache
from scm import MercurialSourceControl
from indexer import WhooshWikiIndex
from auth import UserManager


class FormatterNotFound(Exception):
    pass


class PageFormattingContext(object):
    def __init__(self, url, ext):
        self.url = url
        self.ext = ext
        self.out_links = []
        self.meta = {}

    @property
    def urldir(self):
        return os.path.dirname(self.url)


class PageFormatter(object):
    def __init__(self, wiki):
        self.wiki = wiki

    def formatText(self, ctx, text):
        text = self._preProcessWikiSyntax(ctx, text)
        formatter = self._getFormatter(ctx.ext)
        text = formatter(text)
        text = self._postProcessWikiSyntax(ctx, text)
        return formatter(text)

    def _getFormatter(self, extension):
        formatter = None
        for k, v in self.wiki.formatters.iteritems():
            if extension in v:
                return k
        raise FormatterNotFound("No formatter mapped to file extension: " + extension)

    def _preProcessWikiSyntax(self, ctx, text):
        text = self._processWikiMeta(ctx, text)
        text = self._processWikiLinks(ctx, text)
        return text

    def _postProcessWikiSyntax(self, ctx, text):
        return text

    def _processWikiMeta(self, ctx, text):
        def repl1(m):
            ctx.meta[str(m.group(1))] = str(m.group(3)) if m.group(3) is not None else True
            return ''
        text = re.sub(r'^\[\[((__|\+)?[a-zA-Z][a-zA-Z0-9_\-]+):\s*(.*)\]\]\s*$', repl1, text, flags=re.MULTILINE)
        return text

    def _processWikiLinks(self, ctx, text):
        s = self

        # [[display name|Whatever/PageName]]
        def repl1(m):
            return s._formatWikiLink(ctx, m.group(1), m.group(2))
        text = re.sub(r'\[\[([^\|\]]+)\|([^\]]+)\]\]', repl1, text)

        # [[Namespace/PageName]]
        def repl2(m):
            a, b = m.group(1, 2)
            url = b if a is None else (a + b)
            return s._formatWikiLink(ctx, b, url)
        text = re.sub(r'\[\[([^\]]+/)?([^\]]+)\]\]', repl2, text)

        return text

    def _formatWikiLink(self, ctx, display, url):
        slug = Page.title_to_url(os.path.join(ctx.urldir, url))
        ctx.out_links.append(slug)

        css_class = 'wiki-link'
        if not self.wiki.pageExists(slug):
            css_class += ' missing'
        return '<a class="%s" data-wiki-url="%s">%s</a>' % (css_class, slug, display)


class Page(object):
    def __init__(self, wiki, url):
        self.wiki = wiki
        self.url = url
        self._meta = None

    @property
    def title(self):
        self._ensureMeta()
        return self._meta['title']

    @property
    def raw_text(self):
        if self._meta is not None:
            return self._meta['content']
        page = self.wiki.fs.getPage(self.url)
        return page['content']

    @property
    def formatted_text(self):
        self._ensureMeta()
        return self._meta['formatted']

    @property
    def out_links(self):
        self._ensureMeta()
        return self._meta['out_links']

    @property
    def in_links(self):
        links = []
        for other_url in self.wiki.getPageUrls():
            if other_url == self.url:
                continue
            other_page = Page(self.wiki, other_url)
            for l in other_page.out_links:
                if l == self.url:
                    links.append(other_url)
        return links

    @property
    def all_meta(self):
        self._ensureMeta()
        meta = {
                'url': self._meta['url'],
                'name': self._meta['name'],
                'title': self._meta['title'],
                'user': self._meta['user']
                }
        for name in self._promoted_meta:
            if name in self._meta['user']:
                meta[name] = self._meta['user'][name]
        return meta

    def getHistory(self):
        self._ensureMeta()
        return self.wiki.scm.getHistory(self._meta['path'])

    def getState(self):
        self._ensureMeta()
        return self.wiki.scm.getState(self._meta['path'])

    def getRevision(self, rev):
        self._ensureMeta()
        return self.wiki.scm.getRevision(self._meta['path'], rev)

    def getDiff(self, rev1, rev2):
        self._ensureMeta()
        return self.wiki.scm.diff(self._meta['path'], rev1, rev2)

    def _ensureMeta(self):
        if self._meta is not None:
            return

        cache_key = self.url + '.info.cache'
        cached_meta = self._getCached(cache_key)
        if cached_meta is not None:
            self._meta = cached_meta
            return

        self._meta = self.wiki.fs.getPage(self.url)

        ext = self._meta['ext']
        if ext[0] == '.':
            ext = ext[1:]
        ctx = PageFormattingContext(self.url, ext)
        f = PageFormatter(self.wiki)
        self._meta['formatted'] = f.formatText(ctx, self._meta['content'])
        self._meta['user'] = ctx.meta

        self._meta['title'] = re.sub(r'\-', ' ', self._meta['name'])
        for name in self._promoted_meta:
            if name in ctx.meta:
                self._meta[name] = ctx.meta[name]

        self._meta['out_links'] = []
        for l in ctx.out_links:
            self._meta['out_links'].append(l)

        self._putCached(cache_key, self._meta)

    def _getCached(self, cache_key):
        if self.wiki.cache is not None:
            page_path = self.wiki.fs.getPhysicalPagePath(self.url)
            page_time = os.path.getmtime(page_path)
            return self.wiki.cache.read(cache_key, page_time)
        return None

    def _putCached(self, cache_key, data):
        if self.wiki.cache is not None:
            self.wiki.logger.debug("Updated cached %s for page '%s'." % (cache_key, self.url))
            self.wiki.cache.write(cache_key, data)

    _promoted_meta = [
            'title',
            'redirect',
            'notitle'
            ]

    @staticmethod
    def title_to_url(title):
        return re.sub(r'[^A-Za-z0-9_\.\-\(\)/]+', '-', title.lower())


class Wiki(object):
    def __init__(self, root=None, logger=None):
        if root is None:
            root = os.getcwd()

        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger('wikked.wiki')
        self.logger.debug("Initializing wiki at: " + root)

        self.config = SafeConfigParser()
        config_path = os.path.join(root, '.wikirc')
        if os.path.isfile(config_path):
            self.config.read(config_path)

        self.fs = FileSystem(root)
        self.scm = MercurialSourceControl(root, self.logger)
        self.cache = None #Cache(os.path.join(root, '.cache'))
        self.index = WhooshWikiIndex(os.path.join(root, '.index'), logger=self.logger)
        self.auth = UserManager(self.config, logger=self.logger)

        self.fs.excluded.append(config_path)
        if self.cache is not None:
            self.fs.excluded.append(self.cache.cache_dir)
        if self.scm is not None:
            self.fs.excluded += self.scm.getSpecialDirs()
        if self.index is not None:
            self.fs.excluded.append(self.index.store_dir)

        self.formatters = {
                markdown.markdown: [ 'md', 'mdown', 'markdown' ],
                self._passthrough: [ 'txt', 'text', 'html' ]
                }
        self.fs.page_extensions = list(set(itertools.chain(*self.formatters.itervalues())))

        if self.index is not None:
            self.index.update(self.getPages())

    @property
    def root(self):
        return self.fs.root

    def getPageUrls(self, subdir=None):
        for info in self.fs.getPageInfos(subdir):
            yield info['url']

    def getPages(self, subdir=None):
        for url in self.getPageUrls(subdir):
            yield Page(self, url)

    def getPage(self, url):
        return Page(self, url)

    def setPage(self, url, page_fields):
        if 'author' not in page_fields:
            raise ValueError("No author specified for editing page '%s'." % url)
        if 'message' not in page_fields:
            raise ValueError("No commit message specified for editing page '%s'." % url)

        do_commit = False
        path = self.fs.getPhysicalPagePath(url)

        if 'text' in page_fields:
            with open(path, 'w') as f:
                f.write(page_fields['text'])
            do_commit = True

        if do_commit:
            commit_meta = {
                    'author': page_fields['author'],
                    'message': page_fields['message']
                    }
            self.scm.commit([ path ], commit_meta)

        if self.index is not None:
            self.index.update([ self.getPage(url) ])

    def pageExists(self, url):
        return self.fs.pageExists(url)

    def getHistory(self):
        return self.scm.getHistory();

    def _passthrough(self, content):
        return content

