import re
import pystache
from metautils import get_meta_name_and_modifiers


class CircularIncludeError(Exception):
    """ An exception raised when a circular include is found
        while rendering a page.
    """
    def __init__(self, message, url_trail):
        Exception.__init__(self, message)
        self.url_trail = url_trail


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
        if page:
            self.meta = dict(page._getLocalMeta())
            self.out_links = list(page._getLocalLinks())

    def add(self, other):
        self.out_links += other.out_links
        for original_key, val in other.meta.iteritems():
            # Ignore internal properties. Strip include-only properties
            # from their prefix.
            key, mod = get_meta_name_and_modifiers(original_key)
            if mod == '__':
                continue

            if key not in self.meta:
                self.meta[key] = val
            else:
                self.meta[key].append(val)


class PageResolver(object):
    """ An object responsible for resolving page queries like
        `include` or `query`.
    """
    default_parameters = {
        '__header': "<ul>\n",
        '__footer': "</ul>\n",
        '__item': "<li><a class=\"wiki-link\" data-wiki-url=\"{{url}}\">" +
            "{{title}}</a></li>\n",
        '__empty': "<p>No page matches the query.</p>\n"
        }

    def __init__(self, page, ctx=None):
        self.page = page
        self.ctx = ctx
        self.output = None

    @property
    def wiki(self):
        return self.page.wiki

    def run(self):
        if not self.ctx:
            self.ctx = ResolveContext(self.page.url)

        # Resolve link states.
        def repl1(m):
            url = str(m.group('url'))
            if self.wiki.pageExists(url):
                return str(m.group())
            return '<a class="wiki-link missing" data-wiki-url="%s">' % url
        
        formatted_text = re.sub(
                r'<a class="wiki-link" data-wiki-url="(?P<url>[^"]+)">',
                repl1,
                self.page._getFormattedText())

        # Resolve queries, includes, etc.
        def repl2(m):
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

        self.output = ResolveOutput(self.page)
        self.output.text = re.sub(
                r'^<div class="wiki-(?P<name>[a-z]+)"'
                r'(?P<opts>( data-wiki-([a-z]+)="([^"]+)")*)'
                r'>(?P<value>.*)</div>$',
                repl2,
                formatted_text,
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
            arg_pattern = r"(^|\|)\s*((?P<name>[a-zA-Z][a-zA-Z0-9_\-]+)\s*=)?(?P<value>[^\|]+)"
            for i, m in enumerate(re.finditer(arg_pattern, args)):
                key = str(m.group('name')).lower()
                value = str(m.group('value')).strip()
                parameters[key] = value
                parameters[str(i + 1)] = value

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
        arg_pattern = r"(^|\|)\s*(?P<name>[a-zA-Z][a-zA-Z0-9_\-]+)\s*="\
            r"(?P<value>[^\|]+)"
        for m in re.finditer(arg_pattern, query):
            key = m.group('name').lower()
            if key in parameters:
                parameters[key] = str(m.group('value'))
            else:
                meta_query[key] = str(m.group('value'))

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
            return self._valueOrPageText(parameters['__empty'])

        # Combine normal templates to build the output.
        text = self._valueOrPageText(parameters['__header'])
        for p in matched_pages:
            tokens = {
                    'url': p.url,
                    'title': p.title
                    }
            tokens.update(p._getLocalMeta())
            text += self._renderTemplate(
                    self._valueOrPageText(parameters['__item']),
                    tokens)
        text += self._valueOrPageText(parameters['__footer'])

        return text

    def _valueOrPageText(self, value):
        if re.match(r'^\[\[.*\]\]$', value):
            page = self.wiki.getPage(value[2:-2])
            return page.text
        return value

    def _isPageMatch(self, page, name, value, level=0):
        # Check the page's local meta properties.
        meta_keys = [name]
        if level > 0:
            # If this is an include, also look for 'include-only'
            # meta properties.
            meta_keys.append('+' + name)
        for key in meta_keys:
            actual = page._getLocalMeta().get(key)
            if (actual is not None and
                    ((type(actual) is list and value in actual) or
                    (actual == value))):
                return True

        # Gather included pages' URLs.
        # If this is an include, also look for `+include`'d pages,
        # and if not, `__include`'d pages.
        include_meta_values = []
        include_meta_keys = ['include']
        if level > 0:
            include_meta_keys.append('+include')
        else:
            include_meta_keys.append('__include')
        for key in include_meta_keys:
            i = page._getLocalMeta().get(key)
            if i is not None:
                if (type(i) is list):
                    include_meta_values += i
                else:
                    include_meta_values.append(i)
        included_urls = []
        for v in include_meta_values:
            pipe_idx = v.find('|')
            if pipe_idx > 0:
                included_urls.append(v[:pipe_idx])
            else:
                included_urls.append(v)

        # Recurse into included pages.
        for url in included_urls:
            p = self.wiki.getPage(url)
            if self._isPageMatch(p, name, value, level + 1):
                return True

        return False

    def _renderTemplate(self, text, parameters):
        renderer = pystache.Renderer(search_dirs=[])
        return renderer.render(text, parameters)

