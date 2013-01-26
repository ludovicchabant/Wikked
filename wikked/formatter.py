import os
import os.path
import re


class FormatterNotFound(Exception):
    pass


class CircularIncludeError(Exception):
    def __init__(self, message, url_trail):
        Exception.__init__(self, message)
        self.url_trail = url_trail


class BaseContext(object):
    def __init__(self, url, slugify=None):
        self.url = url
        self.slugify = slugify

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
            abs_url = self.slugify(abs_url)
        return abs_url


class FormattingContext(BaseContext):
    def __init__(self, url, ext, slugify):
        BaseContext.__init__(self, url, slugify)
        self.ext = ext
        self.out_links = []
        self.included_pages = []
        self.meta = {}


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
            meta_name = str(m.group(1)).lower()
            meta_value = str(m.group(3))
            if meta_value is not None and len(meta_value) > 0:
                if meta_name not in ctx.meta:
                    ctx.meta[meta_name] = meta_value
                elif ctx.meta[meta_name] is list:
                    ctx.meta[meta_name].append(meta_value)
                else:
                    ctx.meta[meta_name] = [ctx.meta[meta_name], meta_value]
            else:
                ctx.meta[meta_name] = True
            if meta_name == 'include':
                return self._processInclude(ctx, meta_value)
            elif meta_name == 'query':
                return self._processQuery(ctx, meta_value)
            return ''

        text = re.sub(r'^\{\{((__|\+)?[a-zA-Z][a-zA-Z0-9_\-]+):\s*(.*)\}\}\s*$', repl, text, flags=re.MULTILINE)
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
        included_url = ctx.getAbsoluteUrl(value)
        ctx.included_pages.append(included_url)
        # Includes are run on the fly.
        return '<div class="wiki-include">%s</div>\n' % included_url

    def _processQuery(self, ctx, query):
        # Queries are run on the fly.
        return '<div class="wiki-query">%s</div>\n' % query

    def _formatWikiLink(self, ctx, display, url):
        abs_url = ctx.getAbsoluteUrl(url)
        ctx.out_links.append(abs_url)

        css_class = 'wiki-link'
        if not self.wiki.pageExists(abs_url, from_db=False):
            css_class += ' missing'
        return '<a class="%s" data-wiki-url="%s">%s</a>' % (css_class, abs_url, display)


class ResolvingContext(object):
    def __init__(self):
        self.url_trail = set()
        self.meta = {}
        self.out_links = []
        self.included_pages = []

    def add(self, ctx):
        self.url_trail += ctx.url_trail
        self.out_links += ctx.out_links
        self.included_pages += ctx.included_pages
        for original_key, val in ctx.meta.iteritems():
            # Ignore internal properties. Strip include-only properties
            # from their prefix.
            key = original_key
            if key[0:2] == '__':
                continue
            if key[0] == '+':
                key = key[1:]

            if key not in self.meta:
                self.meta[key] = val
            elif self.meta[key] is list:
                self.meta[key].append(val)
            else:
                self.meta[key] = [self.meta[key], val]


class PageResolver(object):
    default_parameters = {
        'header': "<ul>",
        'footer': "</ul>",
        'item': "<li><a class=\"wiki-link\" data-wiki-url=\"{{url}}\">" +
            "{{title}}</a></li>",
        'empty': "<p>No page matches the query.</p>"
        }

    def __init__(self, page, ctx):
        self.page = page
        self.ctx = ctx

    @property
    def wiki(self):
        return self.page.wiki

    def run(self):
        def repl(m):
            meta_name = str(m.group(1))
            meta_value = str(m.group(2))
            if meta_name == 'query':
                return self._runQuery(meta_value)
            elif meta_name == 'include':
                return self._runInclude(meta_value)
            return ''

        self.ctx.url_trail = [self.page.url]
        self.ctx.out_links = self.page.local_links
        self.ctx.included_pages = self.page.local_includes
        self.ctx.meta = self.page.local_meta

        text = self.page.formatted_text
        return re.sub(r'^<div class="wiki-([a-z]+)">(.*)</div>$', repl, text,
            flags=re.MULTILINE)

    def _runInclude(self, include_url):
        if include_url in self.ctx.url_trail:
            raise CircularIncludeError("Circular include detected at: %s" % include_url, self.ctx.url_trail)
        page = self.wiki.getPage(include_url)
        child_ctx = ResolvingContext()
        child = PageResolver(page, child_ctx)
        text = child.run()
        self.ctx.add(child_ctx)
        return text

    def _runQuery(self, query):
        # Parse the query.
        parameters = dict(self.default_parameters)
        meta_query = {}
        arg_pattern = r"(^|\|)(?P<name>[a-zA-Z][a-zA-Z0-9_\-]+)="\
            r"(?P<value>[^\|]+)"
        for m in re.findall(arg_pattern, query):
            key = m[1].lower()
            if key not in parameters:
                meta_query[key] = m[2]
            else:
                parameters[key] = m[2]

        # Find pages that match the query, excluding any page
        # that is in the URL trail.
        matched_pages = []
        for p in self.wiki.getPages():
            if p.url in self.ctx.url_trail:
                continue
            for key, value in meta_query.iteritems():
                if self._isPageMatch(p, key, value):
                    matched_pages.append(p)

        # No match: return the 'empty' template.
        if len(matched_pages) == 0:
            return parameters['empty']

        # Combine normal templates to build the output.
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

    def _isPageMatch(self, page, name, value, level=0):
        # Check the page's local meta properties.
        actual = page.local_meta.get(name)
        if ((type(actual) is list and value in actual) or
            (actual == value)):
            return True

        # If this is an include, also look for 'include-only'
        # meta properties.
        if level > 0:
            actual = page.local_meta.get('+' + name)
            if ((type(actual) is list and value in actual) or
                (actual == value)):
                return True

        # Recurse into included pages.
        for url in page.local_includes:
            p = self.wiki.getPage(url)
            if self._isPageMatch(p, name, value, level + 1):
                return True
