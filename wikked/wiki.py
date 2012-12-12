import os
import os.path
import re
import time
import logging
from itertools import chain
import markdown
from fs import FileSystem
from cache import Cache
from scm import MercurialSourceControl


class FormatterNotFound(Exception):
    pass


class PageFormattingContext(object):
    def __init__(self, url, ext):
        self.url = url
        self.ext = ext
        self.out_links = []
        self.title = None


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
            ctx.title = m.group(1)
            return ''
        text = re.sub(r'^\[\[title:\s*(.+)\]\]\s*$', repl1, text, flags=re.MULTILINE)
        return text

    def _processWikiLinks(self, ctx, text):
        s = self

        # [[display name|Whatever/PageName]]
        def repl1(m):
            ctx.out_links.append(m.group(2))
            return s._formatWikiLink(m.group(1), m.group(2))
        text = re.sub(r'\[\[([^\|\]]+)\|([^\]]+)\]\]', repl1, text)

        # [[Namespace/PageName]]
        def repl2(m):
            a, b = m.group(1, 2)
            url = b if a is None else (a + b)
            ctx.out_links.append(url)
            return s._formatWikiLink(b, url)
        text = re.sub(r'\[\[([^\]]+/)?([^\]]+)\]\]', repl2, text)

        return text

    def _formatWikiLink(self, display, url):
        slug = re.sub(r'[^A-Za-z0-9_\.\-\(\)/]+', '-', url.lower())
        return '<a class="wiki-link" data-wiki-url="%s">%s</a>' % (slug, display)


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
        for other_url in self.wiki.getPageNames():
            if other_url == self.url:
                continue
            other_page = Page(self.wiki, other_url)
            for l in other_page.out_links:
                if l == self.url:
                    links.append(other_url)
        return links

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

        self._meta['title'] = re.sub(r'\-', ' ', self._meta['name'])
        if ctx.title is not None:
            self._meta['title'] = ctx.title

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


class Wiki(object):
    def __init__(self, root=None, logger=None):
        if root is None:
            root = os.getcwd()

        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger('wikked.wiki')
        self.logger.debug("Initializing wiki at: " + root)

        self.fs = FileSystem(root)
        self.scm = MercurialSourceControl(root, self.logger)
        self.cache = None #Cache(os.path.join(root, '.cache'))

        if self.cache is not None:
            self.fs.excluded.append(self.cache.cache_dir)
        if self.scm is not None:
            self.fs.excluded += self.scm.getSpecialDirs()

        self.formatters = {
                markdown.markdown: [ 'md', 'mdown', 'markdown' ],
                self._passthrough: [ 'txt', 'text', 'html' ]
                }

    @property
    def root(self):
        return self.fs.root

    def getPageNames(self, subdir=None):
        return self.fs.getPageNames(subdir)

    def getPage(self, url):
        page = Page(self, url)
        return page

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

    def getPageHistory(self, url):
        path = self.fs.getPhysicalPagePath(url)
        return self.scm.getHistory(path)

    def getPageState(self, url):
        path = self.fs.getPhysicalPagePath(url)
        return self.scm.getState(path)

    def _passthrough(self, content):
        return content

