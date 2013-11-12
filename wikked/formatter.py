import os
import os.path
import re
from utils import get_meta_name_and_modifiers


class BaseContext(object):
    """ Base context for formatting pages. """
    def __init__(self, url):
        self.url = url

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
    def __init__(self, wiki):
        self.wiki = wiki
        self.coercers = {
                'include': self._coerceInclude
                }
        self.processors = {
                'include': self._processInclude,
                'query': self._processQuery
                }

    def formatText(self, ctx, text):
        text = self._processWikiSyntax(ctx, text)
        return text

    def _processWikiSyntax(self, ctx, text):
        text = self._processWikiMeta(ctx, text)
        text = self._processWikiLinks(ctx, text)
        return text

    def _processWikiMeta(self, ctx, text):
        def repl(m):
            meta_name = str(m.group('name')).lower()
            meta_value = str(m.group('value'))

            if meta_value is None or meta_value == '':
                # No value provided: this is a "flag" meta.
                ctx.meta[meta_name] = True
                return ''

            # If we actually have a value, coerce it, if applicable,
            # and get the name without the modifier prefix.
            clean_meta_name, meta_modifier = get_meta_name_and_modifiers(meta_name)
            coerced_meta_value = meta_value
            if clean_meta_name in self.coercers:
                coerced_meta_value = self.coercers[clean_meta_name](ctx, meta_value)

            # Then, set the value on the meta dictionary, or add it to
            # other existing meta values with the same key.
            if meta_name not in ctx.meta:
                ctx.meta[meta_name] = [coerced_meta_value]
            else:
                ctx.meta[meta_name].append(coerced_meta_value)

            # Process it, or remove it from the output text.
            if clean_meta_name in self.processors:
                return self.processors[clean_meta_name](ctx, meta_modifier, coerced_meta_value)
            return ''

        # Single line meta.
        text = re.sub(
                r'^\{\{(?P<name>(__|\+)?[a-zA-Z][a-zA-Z0-9_\-]+):\s*(?P<value>.*)\}\}\s*$',
                repl,
                text,
                flags=re.MULTILINE)
        # Multi-line meta.
        text = re.sub(
                r'^\{\{(?P<name>(__|\+)?[a-zA-Z][a-zA-Z0-9_\-]+):\s*(?P<value>.*)^\}\}\s*$',
                repl,
                text,
                flags=re.MULTILINE | re.DOTALL)
        return text

    def _processWikiLinks(self, ctx, text):
        s = self

        # [[url:Something/Blah.ext]]
        def repl1(m):
            url = m.group(1).strip()
            if url.startswith('/'):
                return '/files' + url
            abs_url = os.path.join('/files', ctx.urldir, url)
            abs_url = os.path.normpath(abs_url).replace('\\', '/')
            return abs_url
        text = re.sub(r'\[\[url\:([^\]]+)\]\]', repl1, text)

        # [[display name|Whatever/PageName]]
        def repl2(m):
            return s._formatWikiLink(ctx, m.group(1).strip(), m.group(2).strip())
        text = re.sub(r'\[\[([^\|\]]+)\|([^\]]+)\]\]', repl2, text)

        # [[Namespace/PageName]]
        def repl3(m):
            a, b = m.group(1, 2)
            url = b if a is None else (a + b)
            return s._formatWikiLink(ctx, b, url)
        text = re.sub(r'\[\[([^\]]+/)?([^\]]+)\]\]', repl3, text)

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
        # Includes are run on the fly.
        pipe_idx = value.find('|')
        if pipe_idx < 0:
            included_url = value
            parameters = ''
        else:
            included_url = value[:pipe_idx]
            parameters = value[pipe_idx + 1:]

        url_attr = ' data-wiki-url="%s"' % included_url
        mod_attr = ''
        if modifier:
            mod_attr = ' data-wiki-mod="%s"' % modifier
        return '<div class="wiki-include"%s%s>%s</div>\n' % (url_attr, mod_attr, parameters)

    def _processQuery(self, ctx, modifier, query):
        # Queries are run on the fly.
        # But we pre-process arguments that reference other pages,
        # so that we get the absolute URLs right away.
        processed_args = ''
        arg_pattern = r"(^|\|)\s*(?P<name>[a-zA-Z][a-zA-Z0-9_\-]+)\s*="\
            r"(?P<value>[^\|]+)"
        for m in re.finditer(arg_pattern, query):
            name = str(m.group('name')).strip()
            value = str(m.group('value')).strip()
            processed_args += '%s=%s' % (name, value)

        mod_attr = ''
        if modifier:
            mod_attr = ' data-wiki-mod="%s"' % modifier
        return '<div class="wiki-query"%s>%s</div>\n' % (mod_attr, processed_args)

    def _formatWikiLink(self, ctx, display, url):
        ctx.out_links.append(url)
        return '<a class="wiki-link" data-wiki-url="%s">%s</a>' % (url, display)

    @staticmethod
    def parseWikiLinks(text):
        urls = []
        pattern = r"<a class=\"[^\"]*\" data-wiki-url=\"(?P<url>[^\"]+)\">"
        for m in re.finditer(pattern, text):
            urls.append(str(m.group('url')))
        return urls

