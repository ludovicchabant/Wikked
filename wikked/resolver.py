import re
import urllib
import os.path
import logging
import jinja2
from utils import (
        PageNotFoundError,
        get_meta_name_and_modifiers, get_absolute_url,
        html_unescape)


logger = logging.getLogger(__name__)


class FormatterNotFound(Exception):
    """ An exception raised when not formatter is found for the
        current page.
    """
    pass


class IncludeError(Exception):
    """ An exception raised when an include cannot be resolved.
    """
    def __init__(self, include_url, ref_url, message=None, *args):
        Exception.__init__(self, include_url, ref_url, message, *args)

    def __str__(self):
        include_url = self.args[0]
        ref_url = self.args[1]
        message = self.args[2]
        res = "Error including '%s' from '%s'." % (include_url, ref_url)
        if message:
            res += " " + message
        return res


class CircularIncludeError(IncludeError):
    """ An exception raised when a circular include is found
        while rendering a page.
    """
    def __init__(self, include_url, ref_url, url_trail):
        IncludeError.__init__(self, include_url, ref_url, None, url_trail)

    def __str__(self):
        url_trail = self.args[3]
        res = IncludeError.__init__(self)
        res += " Circular include detected after: %s" % url_trail
        return res


class ResolveContext(object):
    """ The context for resolving page queries. """
    def __init__(self, root_page=None):
        self.root_page = root_page
        self.url_trail = []
        if root_page:
            self.url_trail.append(root_page.url)

    def shouldRunMeta(self, modifier):
        if modifier is None:
            return True
        if modifier == '__':
            return len(self.url_trail) <= 1
        if modifier == '+':
            return len(self.url_trail) > 1
        raise ValueError("Unknown modifier: " + modifier)

    def getAbsoluteUrl(self, url, base_url=None, quote=False):
        if base_url is None:
            base_url = self.root_page.url
        return get_absolute_url(base_url, url, quote)


class ResolveOutput(object):
    """ The results of a resolve operation. """
    def __init__(self, page=None):
        self.text = ''
        self.meta = {}
        self.out_links = []
        if page:
            self.meta = dict(page.getLocalMeta())

    def add(self, other):
        for original_key, val in other.meta.iteritems():
            # Ignore internal properties. Strip include-only properties
            # from their prefix.
            key, mod = get_meta_name_and_modifiers(original_key)
            if mod == '__':
                continue

            if key not in self.meta:
                self.meta[key] = val
            else:
                self.meta[key] = list(set(self.meta[key] + val))


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

    def __init__(self, page, ctx=None, parameters=None):
        self.page = page
        self.ctx = ctx or ResolveContext(page)
        self.parameters = parameters
        self.output = None
        self.env = None

        self.resolvers = {
                'query': self._runQuery,
                'include': self._runInclude
            }

    @property
    def wiki(self):
        return self.page.wiki

    @property
    def is_root(self):
        return self.page == self.ctx.root_page

    def run(self):
        try:
            return self._unsafeRun()
        except Exception as e:
            logger.error("Error resolving page '%s':" % self.page.url)
            logger.exception(unicode(e.message))
            self.output = ResolveOutput(self.page)
            self.output.text = u'<div class="error">%s</div>' % e
            return self.output

    def _unsafeRun(self):
        # Create default parameters.
        if not self.parameters:
            urldir = os.path.dirname(self.page.url)
            full_title = os.path.join(urldir, self.page.title).replace('\\', '/')
            self.parameters = {
                '__page': {
                    'url': self.page.url,
                    'title': self.page.title,
                    'full_title': full_title
                    },
                '__args': []
                }

        # Create the output object, so it can be referenced and merged
        # with child outputs (from included pages).
        self.output = ResolveOutput(self.page)

        # Start with the page's text.
        final_text = self.page.getFormattedText()

        # Resolve queries, includes, etc.
        def repl2(m):
            meta_name = unicode(m.group('name'))
            meta_value = unicode(m.group('value'))
            meta_opts = {}
            if m.group('opts'):
                for c in re.finditer(
                        r'data-wiki-(?P<name>[a-z]+)="(?P<value>[^"]+)"',
                        unicode(m.group('opts'))):
                    opt_name = unicode(c.group('name'))
                    opt_value = unicode(c.group('value'))
                    meta_opts[opt_name] = opt_value

            resolver = self.resolvers.get(meta_name)
            if resolver:
                return resolver(meta_opts, meta_value)
            return ''

        final_text = re.sub(
                r'^<div class="wiki-(?P<name>[a-z]+)"'
                r'(?P<opts>( data-wiki-([a-z]+)="([^"]+)")*)'
                r'>(?P<value>.*)</div>$',
                repl2,
                final_text,
                flags=re.MULTILINE)

        # If this is the root page, with all the includes resolved and
        # collapsed into one text, we need to run the final steps.
        if self.is_root:
            # Resolve any `{{foo}}` variable references.
            parameters = dict(self.parameters)
            final_text = self._renderTemplate(final_text, parameters, error_url=self.page.url)

            # Resolve link states.
            def repl1(m):
                raw_url = unicode(m.group('url'))
                url = self.ctx.getAbsoluteUrl(raw_url)
                self.output.out_links.append(url)
                quoted_url = urllib.quote(url.encode('utf-8'))
                if self.wiki.pageExists(url):
                    return '<a class="wiki-link" data-wiki-url="%s">' % quoted_url
                return '<a class="wiki-link missing" data-wiki-url="%s">' % quoted_url

            final_text = re.sub(
                    r'<a class="wiki-link" data-wiki-url="(?P<url>[^"]+)">',
                    repl1,
                    final_text)

            # Format the text.
            formatter = self._getFormatter(self.page.extension)
            final_text = formatter(final_text)

        # Assign the final text and return.
        self.output.text = final_text
        return self.output

    def _runInclude(self, opts, args):
        # Should we even run this include?
        if 'mod' in opts:
            if not self.ctx.shouldRunMeta(opts['mod']):
                return ''

        # Get the included page. First, try with a page in the special
        # `Templates` folder.
        include_url = opts['url']
        if include_url[0] != '/':
            include_url = self.ctx.getAbsoluteUrl(
                    self.page.wiki.templates_url + include_url,
                    self.page.url)
            if not self.wiki.pageExists(include_url):
                include_url = self.ctx.getAbsoluteUrl(opts['url'], self.page.url)
        else:
            include_url = self.ctx.getAbsoluteUrl(include_url, self.page.url)

        # Check for circular includes.
        if include_url in self.ctx.url_trail:
            raise CircularIncludeError(include_url, self.page.url, self.ctx.url_trail)

        # Parse the templating parameters.
        parameters = dict(self.parameters)
        if args:
            # For each parameter, we render templated expressions in case
            # they depend on parent paremeters passed to the call.
            # We do not, however, run them through the formatting -- this
            # will be done in one pass when everything is gathered on the
            # root page.
            arg_pattern = r'<div class="wiki-param" data-name="(?P<name>\w[\w\d]*)?">(?P<value>.*?)</div>'
            for i, m in enumerate(re.finditer(arg_pattern, args)):
                value = unicode(m.group('value')).strip()
                value = html_unescape(value)
                value = self._renderTemplate(value, parameters, error_url=self.page.url)
                if m.group('name'):
                    key = unicode(m.group('name')).lower()
                    parameters[key] = value
                else:
                    parameters['__args'].append(value)

        # Re-run the resolver on the included page to get its final
        # formatted text.
        try:
            page = self.wiki.getPage(include_url)
        except PageNotFoundError:
            raise IncludeError(include_url, self.page.url, "Page not found")
        current_url_trail = list(self.ctx.url_trail)
        self.ctx.url_trail.append(page.url)
        child = PageResolver(page, self.ctx, parameters)
        child_output = child.run()
        self.output.add(child_output)
        self.ctx.url_trail = current_url_trail

        # Run the templating.
        text = child_output.text
        text = self._renderTemplate(text, parameters, error_url=include_url)

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
                parameters[key] = unicode(m.group('value'))
            else:
                meta_query[key] = unicode(m.group('value'))

        # Find pages that match the query, excluding any page
        # that is in the URL trail.
        matched_pages = []
        for p in self.wiki.getPages():
            if p.url in self.ctx.url_trail:
                continue
            for key, value in meta_query.iteritems():
                try:
                    if self._isPageMatch(p, key, value):
                        matched_pages.append(p)
                except Exception as e:
                    logger.error("Can't query page '%s' for '%s':" % (p.url, self.page.url))
                    logger.exception(unicode(e.message))

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
            tokens.update(p.getLocalMeta())
            item_url, item_text = self._valueOrPageText(parameters['__item'], with_url=True)
            text += self._renderTemplate(item_text, tokens, error_url=item_url or self.page.url)
        text += self._valueOrPageText(parameters['__footer'])

        return text

    def _valueOrPageText(self, value, with_url=False):
        if re.match(r'^\[\[.*\]\]$', value):
            include_url = value[2:-2]
            try:
                page = self.wiki.getPage(include_url)
            except PageNotFoundError:
                raise IncludeError(include_url, self.page.url, "Page not found")
            if with_url:
                return (page.url, page.text)
            return page.text

        if with_url:
            return (None, value)
        return value

    def _isPageMatch(self, page, name, value, level=0):
        # Check the page's local meta properties.
        meta_keys = [name]
        if level > 0:
            # If this is an include, also look for 'include-only'
            # meta properties.
            meta_keys.append('+' + name)
        for key in meta_keys:
            actual = page.getLocalMeta().get(key)
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
            i = page.getLocalMeta().get(key)
            if i is not None:
                if (type(i) is list):
                    include_meta_values += i
                else:
                    include_meta_values.append(i)
        included_urls = []
        for v in include_meta_values:
            pipe_idx = v.find('|')
            if pipe_idx > 0:
                v = v[:pipe_idx]

            if v[0] != '/':
                include_url = self.ctx.getAbsoluteUrl(
                        self.page.wiki.templates_url + v,
                        page.url)
                if not self.wiki.pageExists(include_url):
                    include_url = self.ctx.getAbsoluteUrl(v, page.url)
            else:
                include_url = self.ctx.getAbsoluteUrl(v, page.url)
            included_urls.append(include_url)

        # Recurse into included pages.
        for url in included_urls:
            try:
                p = self.wiki.getPage(url)
            except PageNotFoundError:
                raise IncludeError(url, page.url, "Page not found")
            if self._isPageMatch(p, name, value, level + 1):
                return True

        return False

    def _getFormatter(self, extension):
        known_exts = []
        for k, v in self.page.wiki.formatters.iteritems():
            if extension in v:
                return k
            known_exts += v
        raise FormatterNotFound(
            "No formatter mapped to file extension '%s' (known extensions: %s)" %
            (extension, known_exts))

    def _renderTemplate(self, text, parameters, error_url=None):
        env = self._getJinjaEnvironment()
        try:
            template = env.from_string(text)
            return template.render(parameters)
        except jinja2.TemplateSyntaxError as tse:
            raise Exception("Error in '%s': %s\n%s" % (error_url or 'Unknown URL', tse, text))

    def _getJinjaEnvironment(self):
        if self.env is None:
            self.env = jinja2.Environment()
            self.env.globals['read_url'] = generate_read_url
            self.env.globals['edit_url'] = generate_edit_url
        return self.env


def generate_read_url(value, title=None):
    if title is None:
        title = value
    return '<a class="wiki-link" data-wiki-url="%s">%s</a>' % (value, title)

def generate_edit_url(value, title=None):
    if title is None:
        title = value
    return '<a class="wiki-link" data-wiki-url="%s" data-action="edit">%s</a>' % (value, title)

