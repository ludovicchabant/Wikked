import os
import os.path
import re
import types


def get_meta_name_and_modifiers(name):
    """ Strips a meta name from any leading modifiers like `__` or `+`
        and returns both as a tuple. If no modifier was found, the
        second tuple value is `None`.
    """
    clean_name = name
    modifiers = None
    if name[:2] == '__':
        modifiers = '__'
        clean_name = name[3:]
    elif name[0] == '+':
        modifiers = '+'
        clean_name = name[1:]
    return (clean_name, modifiers)


class FormatterNotFound(Exception):
    """ An exception raised when not formatter is found for the
        current page.
    """
    pass


class CircularIncludeError(Exception):
    """ An exception raised when a circular include is found
        while rendering a page.
    """
    def __init__(self, message, url_trail):
        Exception.__init__(self, message)
        self.url_trail = url_trail


class BaseContext(object):
    """ Base context for formatting pages. """
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
    """ Context for formatting pages. """
    def __init__(self, url, ext, slugify):
        BaseContext.__init__(self, url, slugify)
        self.ext = ext
        self.out_links = []
        self.included_pages = []
        self.meta = {}


class PageFormatter(object):
    """ An object responsible for formatting a page, i.e. rendering
        "stable" content (everything except queries run on the fly,
        like `include` or `query`).
    """
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
                elif isinstance(ctx.meta[meta_name], types.StringTypes):
                    ctx.meta[meta_name] = [ctx.meta[meta_name], meta_value]
                else:
                    ctx.meta[meta_name].append(meta_value)
            else:
                ctx.meta[meta_name] = True

            clean_meta_name, meta_modifier = get_meta_name_and_modifiers(meta_name)
            if clean_meta_name == 'include':
                return self._processInclude(ctx, meta_modifier, meta_value)
            elif clean_meta_name == 'query':
                return self._processQuery(ctx, meta_modifier, meta_value)
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

    def _processInclude(self, ctx, modifier, value):
        pipe_idx = value.find('|')
        if pipe_idx < 0:
            included_url = ctx.getAbsoluteUrl(value)
            parameters = ''
        else:
            included_url = ctx.getAbsoluteUrl(value[:pipe_idx])
            parameters = value[pipe_idx + 1:]
        ctx.included_pages.append(included_url)
        # Includes are run on the fly.
        url_attr = ' data-wiki-url="%s"' % included_url
        mod_attr = ''
        if modifier:
            mod_attr = ' data-wiki-mod="%s"' % modifier
        return '<div class="wiki-include"%s%s>%s</div>\n' % (url_attr, mod_attr, parameters)

    def _processQuery(self, ctx, modifier, query):
        # Queries are run on the fly.
        mod_attr = ''
        if modifier:
            mod_attr = ' data-wiki-mod="%s"' % modifier
        return '<div class="wiki-query"%s>%s</div>\n' % (mod_attr, query)

    def _formatWikiLink(self, ctx, display, url):
        abs_url = ctx.getAbsoluteUrl(url)
        ctx.out_links.append(abs_url)

        css_class = 'wiki-link'
        if not self.wiki.pageExists(abs_url, from_db=False):
            css_class += ' missing'
        return '<a class="%s" data-wiki-url="%s">%s</a>' % (css_class, abs_url, display)


class ResolveContext(object):
    """ The context for resolving page queries. """
    def __init__(self, root_url=None):
        self.url_trail = set()
        if root_url:
            self.url_trail.add(root_url)

    def shouldRunMeta(self, modifier):
        if modifier is None:
            return True
        if modifier == '__':
            return len(self.url_trail) <= 1
        if modifier == '+':
            return len(self.url_trail) > 1
        raise ValueError("Unknown modifier: " + modifier)


class ResolveOutput(object):
    """ The results of a resolve operation. """
    def __init__(self, page=None):
        self.text = ''
        self.meta = {}
        self.out_links = []
        self.included_pages = []
        if page:
            self.meta = dict(page.local_meta)
            self.out_links = list(page.local_links)
            self.included_pages = list(page.local_includes)

    def add(self, other):
        self.out_links += other.out_links
        self.included_pages += other.included_pages
        for original_key, val in other.meta.iteritems():
            # Ignore internal properties. Strip include-only properties
            # from their prefix.
            key, mod = get_meta_name_and_modifiers(original_key)
            if mod == '__':
                continue

            if key not in self.meta:
                self.meta[key] = val
            elif self.meta[key] is list:
                self.meta[key].append(val)
            else:
                self.meta[key] = [self.meta[key], val]


class PageResolver(object):
    """ An object responsible for resolving page queries like
        `include` or `query`.
    """
    default_parameters = {
        'header': "<ul>",
        'footer': "</ul>",
        'item': "<li><a class=\"wiki-link\" data-wiki-url=\"{{url}}\">" +
            "{{title}}</a></li>",
        'empty': "<p>No page matches the query.</p>"
        }

    def __init__(self, page, ctx=None):
        self.page = page
        self.ctx = ctx
        self.output = None

    @property
    def wiki(self):
        return self.page.wiki

    def run(self):
        def repl(m):
            meta_name = str(m.group('name'))
            meta_value = str(m.group('value'))
            meta_opts = {}
            if m.group('opts'):
                for c in re.finditer(
                        r'data-wiki-(?P<name>[a-z]+)="(?P<value>[^"]+)"', 
                        str(m.group('opts'))):
                    opt_name = str(c.group('name'))
                    opt_value = str(c.group('value'))
                    meta_opts[opt_name] = opt_value

            if meta_name == 'query':
                return self._runQuery(meta_opts, meta_value)
            elif meta_name == 'include':
                return self._runInclude(meta_opts, meta_value)
            return ''

        if not self.ctx:
            self.ctx = ResolveContext(self.page.url)

        self.output = ResolveOutput(self.page)
        self.output.text = re.sub(r'^<div class="wiki-(?P<name>[a-z]+)"'
                r'(?P<opts>( data-wiki-([a-z]+)="([^"]+)")*)'
                r'>(?P<value>.*)</div>$',
                repl, 
                self.page.formatted_text,
                flags=re.MULTILINE)
        return self.output

    def _runInclude(self, opts, args):
        # Should we even run this include?
        if 'mod' in opts:
            if not self.ctx.shouldRunMeta(opts['mod']):
                return ''

        # Check for circular includes.
        include_url = opts['url']
        if include_url in self.ctx.url_trail:
            raise CircularIncludeError("Circular include detected at: %s" % include_url, self.ctx.url_trail)

        # Parse the templating parameters.
        parameters = None
        if args:
            parameters = {}
            arg_pattern = r"(^|\|)(?P<name>[a-zA-Z][a-zA-Z0-9_\-]+)=(?P<value>[^\|]+)"
            for m in re.finditer(arg_pattern, args):
                key = str(m.group('name')).lower()
                parameters[key] = str(m.group('value'))

        # Re-run the resolver on the included page to get its final
        # formatted text.
        page = self.wiki.getPage(include_url)
        self.ctx.url_trail.add(page.url)
        child = PageResolver(page, self.ctx)
        child_output = child.run()
        self.output.add(child_output)

        # Run some simple templating if we need to.
        text = child_output.text
        if parameters:
            text = self._renderTemplate(text, parameters)

        return text

    def _runQuery(self, opts, query):
        # Should we even run this query?
        if 'mod' in opts:
            if not self.ctx.shouldRunMeta(opts['mod']):
                return ''

        # Parse the query.
        parameters = dict(self.default_parameters)
        meta_query = {}
        arg_pattern = r"(^|\|)(?P<name>[a-zA-Z][a-zA-Z0-9_\-]+)="\
            r"(?P<value>[^\|]+)"
        for m in re.finditer(arg_pattern, query):
            key = m.group('name').lower()
            if key not in parameters:
                meta_query[key] = m.group('value')
            else:
                parameters[key] = m.group('value')

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
            tokens = {
                    'url': p.url,
                    'title': p.title
                    }
            text += self._renderTemplate(parameters['item'], tokens)
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

    def _renderTemplate(self, text, parameters):
        for token, value in parameters.iteritems():
            text = text.replace('{{%s}}' % token, value)
        return text

