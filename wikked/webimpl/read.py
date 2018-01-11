import os.path
import urllib.parse
from wikked.webimpl import (
    get_redirect_target, get_page_meta, get_page_or_raise,
    make_page_title)
from wikked.utils import split_page_url, PageNotFoundError


def read_page(wiki, user, url, *, no_redirect=False):
    additional_info = {}
    endpoint, path = split_page_url(url)
    if endpoint is None:
        # Normal page.
        page, visited_paths = get_redirect_target(
                wiki, path,
                fields=['url', 'path', 'title', 'text', 'meta'],
                check_perms=(user, 'read'),
                first_only=no_redirect)

        if no_redirect:
            additional_info['redirects_to'] = visited_paths[-1]
        elif len(visited_paths) > 1:
            additional_info['redirected_from'] = visited_paths[:-1]

        ext = os.path.splitext(page.path)[1].lstrip('.')

        result = {'meta': get_page_meta(page), 'text': page.text,
                  'page_title': page.title, 'format': ext}
        result.update(additional_info)
        return result

    # Meta listing page or special endpoint.
    meta_page_url = '%s:%s' % (endpoint, path)
    try:
        info_page = get_page_or_raise(
                wiki, meta_page_url,
                fields=['url', 'path', 'title', 'text', 'meta'],
                check_perms=(user, 'read'))
    except PageNotFoundError:
        # Let permissions errors go through, but if the info page is not
        # found that's OK.
        info_page = None

    info_page_is_default = False
    endpoint_info = wiki.endpoints.get(endpoint)
    if (endpoint_info is not None and endpoint_info.default and
            info_page is None):
        # We have no actual page to show, but we have a default one
        # that we can use for this endpoint.
        info_page = get_page_or_raise(
            wiki, endpoint_info.default,
            fields=['url', 'path', 'title', 'text', 'meta'],
            check_perms=(user, 'read'))
        info_page_is_default = True

    ext = None
    if info_page is not None:
        ext = os.path.splitext(info_page.path)[1].lstrip('.')

    if endpoint_info is not None and not endpoint_info.query:
        # Not a query-based endpoint (like categories). Let's just
        # return the text if it exists, or a "not found" page.
        if info_page is not None:
            result = {
                'endpoint': endpoint,
                'meta': get_page_meta(info_page),
                'text': info_page.text,
                'page_title': info_page.title,
                'format': ext}

            if info_page_is_default:
                # If our page is actually the endpoint's default page
                # because the real page didn't exist, we need to change
                # the title to match the page that we wanted originally.
                # We also fix the URL so navigation links to edit/create
                # the page acts on the wanted page -- not the default info
                # page.
                wanted_page_title = make_page_title(meta_page_url)
                result['page_title'] = wanted_page_title
                result['meta']['title'] = wanted_page_title
                result['meta']['url'] = urllib.parse.quote(
                    meta_page_url.encode('utf-8'))

            result.update(additional_info)
            return result
        raise PageNotFoundError(url)

    # Get the list of pages to show here.
    value = path.lstrip('/')
    value_safe = urllib.parse.quote(value.encode('utf-8'))
    query = {endpoint: [value]}
    pages = wiki.getPages(meta_query=query,
                          fields=['url', 'title', 'text', 'meta'])
    meta = {}
    page_title = value
    if info_page:
        meta = get_page_meta(info_page)
        page_title = info_page.title
    # Need to override the info page's URL and title.
    meta.update({
            'url': urllib.parse.quote(meta_page_url.encode('utf-8')),
            'title': value
            })
    # TODO: skip pages that are forbidden for the current user
    pages_meta = [get_page_meta(p) for p in pages]

    result = {
            'endpoint': endpoint,
            'is_query': True,
            'meta_query': endpoint,
            'meta_value': value,
            'meta_value_safe': value_safe,
            'query': query,
            'query_results': pages_meta,
            'meta': {
                    'url': urllib.parse.quote(meta_page_url.encode('utf-8')),
                    'title': value
                    },
            'page_title': page_title,
            'format': ext
            }
    if info_page:
        result['text'] = info_page.text

    result.update(additional_info)
    return result


def get_incoming_links(wiki, user, url):
    page = get_page_or_raise(
            wiki, url,
            check_perms=(user, 'read'),
            fields=['url', 'title', 'meta'])
    links = []
    for link in page.getIncomingLinks():
        try:
            other = get_page_or_raise(
                    wiki, link,
                    check_perms=(user, 'read'),
                    fields=['url', 'title', 'meta'])
            links.append(get_page_meta(other))
        except PageNotFoundError:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'in_links': links}
    return result


def get_outgoing_links(wiki, user, url):
    page = get_page_or_raise(
            wiki, url,
            check_perms=(user, 'read'),
            fields=['url', 'title', 'links'])
    links = []
    for link in page.links:
        try:
            other = get_page_or_raise(
                    wiki, link,
                    check_perms=(user, 'read'),
                    fields=['url', 'title', 'meta'])
            links.append(get_page_meta(other))
        except PageNotFoundError:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'out_links': links}
    return result
