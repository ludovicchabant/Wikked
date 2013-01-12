import os
import os.path
import re


class FormatterNotFound(Exception):
    pass


class PageFormattingContext(object):
    def __init__(self, url, ext, slugify=None):
        self.url = url
        self.ext = ext
        self.slugify = slugify
        self.out_links = []
        self.included_pages = []
        self.meta = {}

    @property
    def urldir(self):
        return os.path.dirname(self.url)

    def getAbsoluteUrl(self, url):
        if url.startswith('/'):
            # Absolute page URL.
            abs_url = url[1:]
        else:
            # Relative page URL. Let's normalize all `..` in it,
            # which could also replace forward slashes by backslashes
            # on Windows, so we need to convert that back.
            raw_abs_url = os.path.join(self.urldir, url)
            abs_url = os.path.normpath(raw_abs_url).replace('\\', '/')
        if self.slugify is not None:
            abs_url = self.slugify(url)
        return abs_url


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
        def repl(m):
            meta_name = str(m.group(1))
            meta_value = str(m.group(3))
            if meta_value is not None and len(meta_value) > 0:
                if meta_name not in ctx.meta:
                    ctx.meta[meta_name] = meta_value
                elif ctx.meta[meta_name] is list:
                    ctx.meta[meta_name].append(meta_value)
                else:
                    ctx.meta[meta_name] = [ ctx.meta[meta_name], meta_value ]
            else:
                ctx.meta[meta_name] = True
            if meta_name == 'include':
                return self._processInclude(ctx, meta_value)
            elif meta_name == 'query':
                return self._processQuery(ctx, meta_value)
            return ''

        text = re.sub(r'^\[\[((__|\+)?[a-zA-Z][a-zA-Z0-9_\-]+):\s*(.*)\]\]\s*$', repl, text, flags=re.MULTILINE)
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

    def _processInclude(self, ctx, value):
        # TODO: handle self-includes or cyclic includes.
        abs_included_url = ctx.getAbsoluteUrl(value)
        included_page = self.wiki.getPage(abs_included_url)
        ctx.included_pages.append(abs_included_url)
        return included_page.formatted_text

    def _processQuery(self, ctx, query):
        parameters = {
                'header': "<ul>",
                'footer': "</ul>",
                'item': "<li><a class=\"wiki-link\" data-wiki-url=\"{{url}}\">{{title}}</a></li>",
                'empty': "<p>No page matches the query.</p>"
                }
        meta_query = {}
        arg_pattern = r"(^|\|)(?P<name>[a-zA-Z][a-zA-Z0-9_\-]+)=(?P<value>[^\|]+)"
        for m in re.findall(arg_pattern, query):
            if m[1] not in parameters:
                meta_query[m[1]] = m[2]
            else:
                parameters[m[1]] = m[2]

        matched_pages = []
        for p in self.wiki.getPages():
            if p.url == ctx.url:
                continue
            for key, value in meta_query.iteritems():
                actual = p.getUserMeta(key)
                if (type(actual) is list and value in actual) or (actual == value):
                    matched_pages.append(p)
        if len(matched_pages) == 0:
            return parameters['empty']

        text = parameters['header']
        for p in matched_pages:
            item_str = parameters['item']
            tokens = {
                    'url': p.url,
                    'title': p.title
                    }
            for tk, tv in tokens.iteritems():
                item_str = item_str.replace('{{%s}}' % tk, tv)
            text += item_str
        text += parameters['footer']

        return text

    def _formatWikiLink(self, ctx, display, url):
        abs_url = ctx.getAbsoluteUrl(url)
        ctx.out_links.append(abs_url)

        css_class = 'wiki-link'
        if not self.wiki.pageExists(abs_url):
            css_class += ' missing'
        return '<a class="%s" data-wiki-url="%s">%s</a>' % (css_class, abs_url, display)

