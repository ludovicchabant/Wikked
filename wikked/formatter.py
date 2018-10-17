import os
import os.path
import re
import logging
import jinja2
from io import StringIO
from .utils import (
    get_meta_name_and_modifiers, html_escape, split_page_url, get_url_tail)


RE_FILE_FORMAT = re.compile(r'\r\n?', re.MULTILINE)

RE_META_SINGLE_LINE = re.compile(
    r'^\{\{(?P<name>(__|\+)?[a-zA-Z][a-zA-Z0-9_\-]+):\s*(?P<value>.*)\}\}\s*$',
    re.MULTILINE)
RE_META_MULTI_LINE = re.compile(
    r'^\{\{(?P<name>(__|\+)?[a-zA-Z][a-zA-Z0-9_\-]+):\s*'
    r'(?P<value>.*?)^[ \t]*\}\}\s*$',
    re.MULTILINE | re.DOTALL)

RE_LINK_ENDPOINT = re.compile(
    r'(?<!\\)\[\[(\w[\w\d]+)?\:([^\#\]]+)(\#[\w\d\-]+)?\]\]')
RE_LINK_ENDPOINT_DISPLAY = re.compile(
    r'(?<!\\)\[\[([^\|\]]+)\|\s*(\w[\w\d]+)?\:([^\#\]]+)(\#[\w\d\-]+)?\]\]')
RE_LINK_DISPLAY = re.compile(
    r'(?<!\\)\[\[([^\|\]]+)\|([^\#\]]+)(\#[\w\d\-]+)?\]\]')
RE_LINK = re.compile(
    r'(?<!\\)\[\[([^\#\]]+)(\#[\w\d\-]+)?\]\]')
RE_ESCAPED_LINK = re.compile(
    r'(?<!\\)\\\[\[')


logger = logging.getLogger(__name__)


class BaseContext(object):
    """ Base context for formatting pages. """
    def __init__(self, url):
        self.url = url
        self.endpoint, self.endpoint_url = split_page_url(url)

    @property
    def urldir(self):
        return os.path.dirname(self.url)


class FormattingContext(BaseContext):
    """ Context for formatting pages. """
    def __init__(self, url):
        BaseContext.__init__(self, url)
        self.out_links = []
        self.meta = {}


class PageFormatter(object):
    """ An object responsible for formatting a page, i.e. rendering
        "stable" content (everything except queries run on the fly,
        like `include` or `query`).
    """
    def __init__(self):
        self.coercers = {
                'include': self._coerceInclude
                }
        self.processors = {
                'include': self._processInclude,
                'query': self._processQuery
                }
        self.endpoints = {
                'file': self._formatFileLink,
                'image': self._formatImageLink
                }

    def formatText(self, ctx, text):
        text = RE_FILE_FORMAT.sub("\n", text)
        text = self._processWikiSyntax(ctx, text)
        return text

    def _processWikiSyntax(self, ctx, text):
        text = self._processWikiLinks(ctx, text)
        text = self._processWikiMeta(ctx, text)
        return text

    def _processWikiMeta(self, ctx, text):
        def repl(m):
            meta_name = str(m.group('name')).lower()
            meta_value = str(m.group('value'))

            if meta_value is None or meta_value == '':
                # No value provided: this is a "flag" meta.
                ctx.meta[meta_name] = True
                return ''

            # If this is a multi-line meta, strip the trailing new line,
            # since it's there because you must put the ending '}}' on
            # its own line.
            if meta_value[-1] == "\n":
                meta_value = meta_value[:-1]

            # If we actually have a value, coerce it, if applicable,
            # and get the name without the modifier prefix.
            clean_meta_name, meta_modifier = get_meta_name_and_modifiers(
                meta_name)
            coerced_meta_value = meta_value
            if clean_meta_name in self.coercers:
                coerced_meta_value = self.coercers[clean_meta_name](
                    ctx, meta_value)

            # Then, set the value on the meta dictionary, or add it to
            # other existing meta values with the same key.
            if meta_name not in ctx.meta:
                ctx.meta[meta_name] = [coerced_meta_value]
            else:
                ctx.meta[meta_name].append(coerced_meta_value)

            # Process it, or remove it from the output text.
            if clean_meta_name in self.processors:
                return self.processors[clean_meta_name](ctx, meta_modifier,
                                                        coerced_meta_value)
            return ''

        # Single line meta.
        text = RE_META_SINGLE_LINE.sub(repl, text)
        # Multi-line meta.
        text = RE_META_MULTI_LINE.sub(repl, text)

        return text

    def _processWikiLinks(self, ctx, text):
        s = self

        # [[endpoint:Something/Blah.ext]]
        def repl1(m):
            endpoint = m.group(1)
            value, frag = m.group(2, 3)
            name = get_url_tail(value)
            if endpoint in self.endpoints:
                return self.endpoints[endpoint](
                    ctx, endpoint, name.strip(), value.strip(), frag)
            return self._formatEndpointLink(
                ctx, endpoint, name.strip(), value.strip(), frag)
        text = RE_LINK_ENDPOINT.sub(repl1, text)

        # [[display name|endpoint:Something/Whatever]]
        def repl2(m):
            display = m.group(1).strip()
            endpoint = m.group(2)
            value = m.group(3).strip()
            frag = m.group(4)
            if endpoint in self.endpoints:
                return self.endpoints[endpoint](
                    ctx, endpoint, display, value, frag)
            return self._formatEndpointLink(
                ctx, endpoint, display, value, frag)
        text = RE_LINK_ENDPOINT_DISPLAY.sub(repl2, text)

        # [[display name|Whatever/PageName]]
        def repl3(m):
            return s._formatWikiLink(ctx, m.group(1).strip(),
                                     m.group(2).strip(),
                                     m.group(3))
        text = RE_LINK_DISPLAY.sub(repl3, text)

        # [[Namespace/PageName]]
        def repl4(m):
            value, frag = m.group(1, 2)
            name = get_url_tail(value)
            return s._formatWikiLink(ctx, name.strip(), value.strip(), frag)
        text = RE_LINK.sub(repl4, text)

        # \[[Escaped Link]]
        text = RE_ESCAPED_LINK.sub('[[', text)

        return text

    def _coerceInclude(self, ctx, value):
        pipe_idx = value.find('|')
        if pipe_idx < 0:
            return value.strip()
        else:
            url = value[:pipe_idx].strip()
            parameters = value[pipe_idx + 1:].replace('\n', '')
            return url + '|' + parameters

    def _processInclude(self, ctx, modifier, value):
        # Includes are run on the fly, but we preprocess parameters.
        bits = PageFormatter.pipeSplit(value)
        parameters = ''
        included_url = bits[0]
        for p in bits[1:]:
            name = ''
            value = p
            m = re.match('\s*(?P<name>\w[\w\d]*)\s*=(?P<value>.*)', value)
            if m:
                name = str(m.group('name'))
                value = str(m.group('value'))
            value = html_escape(value.strip())
            parameters += ('<div class="wiki-param" data-name="%s">%s</div>' %
                           (name, value))

        url_attr = ' data-wiki-url="%s"' % included_url
        mod_attr = ''
        if modifier:
            mod_attr = ' data-wiki-mod="%s"' % modifier
        return ('<div class="wiki-include"%s%s>%s</div>\n' %
                (url_attr, mod_attr, parameters))

    def _processQuery(self, ctx, modifier, query):
        # Queries are run on the fly.
        # But we pre-process arguments that reference other pages,
        # so that we get the absolute URLs right away.
        processed_args = []
        arg_pattern = r"(\A|\|)\s*(?P<name>(__)?[a-zA-Z][a-zA-Z0-9_\-]+)\s*="\
            r"(?P<value>[^\|]+)"
        for m in re.finditer(arg_pattern, query, re.MULTILINE):
            name = str(m.group('name')).strip()
            value = str(m.group('value')).strip()
            processed_args.append('%s=%s' % (name, value))

        mod_attr = ''
        if modifier:
            mod_attr = ' data-wiki-mod="%s"' % modifier
        return '<div class="wiki-query"%s>%s</div>\n' % (
                mod_attr, '|'.join(processed_args))

    def _formatFileLink(self, ctx, endpoint, display, value, fragment):
        if value.startswith('./'):
            abs_url = os.path.join('/pagefiles', ctx.url.lstrip('/'),
                                   value[2:])
        else:
            abs_url = os.path.join('/files', value.lstrip('/'))
        abs_url = os.path.normpath(abs_url).replace('\\', '/')
        return abs_url

    def _formatImageLink(self, ctx, endpoint, display, value, fragment):
        abs_url = self._formatFileLink(ctx, endpoint, display, value, fragment)
        return ('<img class="wiki-image" src="%s" alt="%s"></img>' %
                (abs_url, display))

    def _formatEndpointLink(self, ctx, endpoint, display, local_url, fragment):
        endpoint = endpoint or ''
        url = '%s:%s' % (endpoint, local_url)
        fragpart = (' data-wiki-fragment="%s"' % fragment) if fragment else ''
        ctx.out_links.append(url)
        return ('<a class="wiki-link" data-wiki-url="%s"'
                '%s'
                ' data-wiki-endpoint="%s">%s</a>' %
                (url, fragpart, endpoint, display))

    def _formatWikiLink(self, ctx, display, url, fragment):
        fragpart = (' data-wiki-fragment="%s"' % fragment) if fragment else ''
        ctx.out_links.append(url)
        return ('<a class="wiki-link" data-wiki-url="%s"'
                '%s>%s</a>' %
                (url, fragpart, display))

    @staticmethod
    def parseWikiLinks(text):
        urls = []
        pattern = r"<a class=\"[^\"]*\" data-wiki-url=\"(?P<url>[^\"]+)\">"
        for m in re.finditer(pattern, text):
            urls.append(str(m.group('url')))
        return urls

    LEXER_STATE_NORMAL = 0
    LEXER_STATE_LINK = 1

    @staticmethod
    def pipeSplit(text):
        res = []
        current = StringIO()
        state = PageFormatter.LEXER_STATE_NORMAL
        env = jinja2.Environment()
        for token in env.lex(text):
            token_type = token[1]
            value = token[2]
            if token_type == 'data':
                for i, c in enumerate(value):
                    if i > 0:
                        if c == '[' and value[i - 1] == '[':
                            state = PageFormatter.LEXER_STATE_LINK
                        elif c == ']' and value[i - 1] == ']':
                            state = PageFormatter.LEXER_STATE_NORMAL
                    if state == PageFormatter.LEXER_STATE_NORMAL and c == '|':
                        res.append(current.getvalue())
                        current.close()
                        current = StringIO()
                    else:
                        current.write(c)
            else:
                current.write(value)
        last_value = current.getvalue()
        if last_value:
            res.append(last_value)
        return res
