import re
import os.path
import urllib.parse
import logging
import jinja2
from wikked.formatter import PageFormatter, FormattingContext
from wikked.utils import (
        PageNotFoundError,
        get_meta_name_and_modifiers, get_absolute_url,
        flatten_single_metas, html_unescape)


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
        for original_key, val in other.meta.items():
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
        '__header': "\n",
        '__footer': "\n",
        '__item': "* [[{{title}}|{{url}}]]\n",
        '__empty': "No page matches the query.\n"
        }

    def __init__(self, page, ctx=None, parameters=None, page_getter=None,
                 pages_meta_getter=None):
        self.page = page
        self.ctx = ctx or ResolveContext(page)
        self.parameters = parameters
        self.page_getter = page_getter or self._getPage
        self.pages_meta_getter = pages_meta_getter or self._getPagesMeta
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
            logger.exception(e.message)
            self.output = ResolveOutput(self.page)
            self.output.text = '<div class="error">%s</div>' % e
            return self.output

    def _getPage(self, url):
        fields = ['url', 'title', 'path', 'formatted_text', 'local_meta',
                  'local_links']
        return self.wiki.db.getPage(url, fields=fields)

    def _getPagesMeta(self):
        fields = ['url', 'title', 'local_meta']
        return self.wiki.db.getPages(fields=fields)

    def _unsafeRun(self):
        # Create default parameters.
        if not self.parameters:
            urldir = os.path.dirname(self.page.url)
            full_title = os.path.join(
                    urldir, self.page.title).replace('\\', '/')
            self.parameters = {
                '__page': {
                    'url': self.page.url,
                    'title': self.page.title,
                    'full_title': full_title
                    },
                '__args': [],
                '__xargs': []
                }

        # Create the output object, so it can be referenced and merged
        # with child outputs (from included pages).
        self.output = ResolveOutput(self.page)

        # Start with the page's text.
        final_text = self.page.getFormattedText()

        # Resolve queries, includes, etc.
        def repl2(m):
            meta_name = m.group('name')
            meta_value = m.group('value')
            meta_opts = {}
            if m.group('opts'):
                for c in re.finditer(
                        r'data-wiki-(?P<name>[a-z]+)="(?P<value>[^"]+)"',
                        m.group('opts')):
                    opt_name = c.group('name')
                    opt_value = c.group('value')
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
            parameters.update(
                    flatten_single_metas(dict(self.page.getLocalMeta())))
            final_text = self._renderTemplate(
                    final_text, parameters, error_url=self.page.url)

            # Resolve link states.
            def repl1(m):
                raw_url = m.group('url')
                is_edit = bool(m.group('isedit'))
                url = self.ctx.getAbsoluteUrl(raw_url)
                self.output.out_links.append(url)
                action = 'edit' if is_edit else 'read'
                quoted_url = urllib.parse.quote(url.encode('utf-8'))
                if self.wiki.pageExists(url):
                    actual_url = '/%s/%s' % (action, quoted_url.lstrip('/'))
                    return ('<a class="wiki-link" data-wiki-url="%s" '
                            'href="%s"' % (quoted_url, actual_url))
                actual_url = '/%s/%s' % (action, quoted_url.lstrip('/'))
                return ('<a class="wiki-link missing" data-wiki-url="%s" '
                        'href="%s"' % (quoted_url, actual_url))

            final_text = re.sub(
                    r'<a class="wiki-link(?P<isedit>-edit)?" '
                    r'data-wiki-url="(?P<url>[^"]+)"',
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
        # `templates` endpoint, if the included page is not specified with an
        # absolute path.
        include_url = opts['url']
        if include_url[0] != '/':
            include_url = self.ctx.getAbsoluteUrl(
                    include_url,
                    self.page.wiki.templates_url)
            if not self.wiki.pageExists(include_url):
                include_url = self.ctx.getAbsoluteUrl(opts['url'],
                                                      self.page.url)
        # else: include URL is absolute.

        # Check for circular includes.
        if include_url in self.ctx.url_trail:
            raise CircularIncludeError(include_url, self.page.url,
                                       self.ctx.url_trail)

        # Parse the templating parameters.
        parameters = dict(self.parameters)
        if args:
            # For each parameter, we render templated expressions in case
            # they depend on parent paremeters passed to the call.
            # We do not, however, run them through the formatting -- this
            # will be done in one pass when everything is gathered on the
            # root page.
            arg_pattern = (r'<div class="wiki-param" '
                           r'data-name="(?P<name>\w[\w\d]*)?">'
                           r'(?P<value>.*?)</div>')
            for i, m in enumerate(re.finditer(arg_pattern, args)):
                value = m.group('value').strip()
                value = html_unescape(value)
                value = self._renderTemplate(value, self.parameters,
                                             error_url=self.page.url)
                if m.group('name'):
                    key = m.group('name').lower()
                    parameters[key] = value
                else:
                    parameters['__xargs'].append(value)
                parameters['__args'].append(value)

        # Re-run the resolver on the included page to get its final
        # formatted text.
        try:
            page = self.page_getter(include_url)
        except PageNotFoundError:
            raise IncludeError(include_url, self.page.url, "Page not found")
        current_url_trail = list(self.ctx.url_trail)
        self.ctx.url_trail.append(page.url)
        child = PageResolver(page, self.ctx, parameters, self.page_getter,
                             self.pages_meta_getter)
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
        arg_pattern = r"(^|\|)\s*(?P<name>(__)?[a-zA-Z][a-zA-Z0-9_\-]+)\s*="\
            r"(?P<value>[^\|]+)"
        for m in re.finditer(arg_pattern, query):
            key = m.group('name').lower()
            if key in parameters:
                parameters[key] = m.group('value')
            else:
                meta_query[key] = m.group('value')

        # Find pages that match the query, excluding any page
        # that is in the URL trail.
        matched_pages = []
        logger.debug("Running page query: %s" % meta_query)
        for p in self.pages_meta_getter():
            if p.url in self.ctx.url_trail:
                continue
            for key, value in meta_query.items():
                try:
                    if self._isPageMatch(p, key, value):
                        matched_pages.append(p)
                except Exception as e:
                    logger.error("Can't query page '%s' for '%s':" % (
                            p.url, self.page.url))
                    logger.exception(e.message)

        # We'll have to format things...
        fmt_ctx = FormattingContext(self.page.url)
        fmt = PageFormatter()

        # No match: return the 'empty' template.
        if len(matched_pages) == 0:
            logger.debug("No pages matched query.")
            tpl_empty = fmt.formatText(
                    fmt_ctx, self._valueOrPageText(parameters['__empty']))
            return tpl_empty

        # Combine normal templates to build the output.
        tpl_header = fmt.formatText(
                fmt_ctx, self._valueOrPageText(parameters['__header']))
        tpl_footer = fmt.formatText(
                fmt_ctx, self._valueOrPageText(parameters['__footer']))
        item_url, tpl_item = self._valueOrPageText(parameters['__item'],
                                                   with_url=True)
        tpl_item = fmt.formatText(fmt_ctx, tpl_item)

        text = tpl_header
        add_trailing_line = tpl_item[-1] == "\n"
        for p in matched_pages:
            tokens = {
                    'url': p.url,
                    'title': p.title}
            page_local_meta = flatten_single_metas(dict(p.getLocalMeta()))
            tokens.update(page_local_meta)
            text += self._renderTemplate(
                    tpl_item, tokens, error_url=item_url or self.page.url)
            if add_trailing_line:
                # Jinja2 eats trailing new lines... :(
                text += "\n"
        text += tpl_footer

        return text

    def _valueOrPageText(self, value, with_url=False):
        stripped_value = value.strip()
        if re.match(r'^\[\[.*\]\]$', stripped_value):
            include_url = stripped_value[2:-2]
            try:
                page = self.page_getter(include_url)
            except PageNotFoundError:
                raise IncludeError(include_url, self.page.url,
                                   "Page not found")
            if with_url:
                return (page.url, page.text)
            return page.text

        if re.match(r'^__[a-zA-Z][a-zA-Z0-9_\-]+$', stripped_value):
            meta = self.page.getLocalMeta(stripped_value)
            if with_url:
                return (None, meta)
            return meta

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
                        v, self.page.wiki.templates_url)
                if not self.wiki.pageExists(include_url):
                    include_url = self.ctx.getAbsoluteUrl(v, page.url)

            included_urls.append(include_url)

        # Recurse into included pages.
        for url in included_urls:
            try:
                p = self.page_getter(url)
            except PageNotFoundError:
                raise IncludeError(url, page.url, "Page not found")
            if self._isPageMatch(p, name, value, level + 1):
                return True

        return False

    def _getFormatter(self, extension):
        known_exts = []
        for k, v in self.page.wiki.formatters.items():
            if extension in v:
                return k
            known_exts += v
        raise FormatterNotFound(
            "No formatter mapped to file extension '%s' "
            "(known extensions: %s)" %
            (extension, known_exts))

    def _renderTemplate(self, text, parameters, error_url=None):
        env = self._getJinjaEnvironment()
        try:
            template = env.from_string(text)
            return template.render(parameters)
        except jinja2.TemplateSyntaxError as tse:
            raise Exception("Error in '%s': %s\n%s" % (
                    error_url or 'Unknown URL', tse, text))

    def _getJinjaEnvironment(self):
        if self.env is None:
            self.env = jinja2.Environment()
            self.env.globals['read_url'] = generate_read_url
            self.env.globals['edit_url'] = generate_edit_url
        return self.env


def generate_read_url(value, title=None):
    if title is None:
        title = value
    return ('<a class="wiki-link" data-wiki-url="%s">%s</a>' %
            (value, title))


def generate_edit_url(value, title=None):
    if title is None:
        title = value
    return ('<a class="wiki-link-edit" data-wiki-url="%s">%s</a>' %
            (value, title))

