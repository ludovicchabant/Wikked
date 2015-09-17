import urllib.parse
from wikked.webimpl import (
        CHECK_FOR_READ,
        get_redirect_target, get_page_meta, get_page_or_raise)
from wikked.utils import split_page_url, PageNotFoundError


def read_page(wiki, user, url, *, no_redirect=False):
    additional_info = {}
    endpoint, path = split_page_url(url)
    if endpoint is None:
        # Normal page.
        page, visited_paths = get_redirect_target(
                wiki, path,
                fields=['url', 'title', 'text', 'meta'],
                check_perms=(user, CHECK_FOR_READ),
                first_only=no_redirect)
        if page is None:
            raise PageNotFoundError(url)

        if no_redirect:
            additional_info['redirects_to'] = visited_paths[-1]
        elif len(visited_paths) > 1:
            additional_info['redirected_from'] = visited_paths[:-1]

        result = {'meta': get_page_meta(page), 'text': page.text,
                  'page_title': page.title}
        result.update(additional_info)
        return result

    # Meta listing page or special endpoint.
    meta_page_url = '%s:%s' % (endpoint, path)
    try:
        info_page = get_page_or_raise(
                wiki, meta_page_url,
                fields=['url', 'title', 'text', 'meta'],
                check_perms=(user, CHECK_FOR_READ))
    except PageNotFoundError:
        # Let permissions errors go through, but if the info page is not
        # found that's OK.
        info_page = None

    endpoint_info = wiki.endpoints.get(endpoint)
    if endpoint_info is not None:
        # We have some information about this endpoint...
        if endpoint_info.default and info_page is None:
            # Default page text.
            info_page = get_page_or_raise(
                    wiki, endpoint_info.default,
                    fields=['url', 'title', 'text', 'meta'],
                    check_perms=(user, CHECK_FOR_READ))

        if not endpoint_info.query:
            # Not a query-based endpoint (like categories). Let's just
            # return the text.
            result = {
                    'endpoint': endpoint,
                    'meta': get_page_meta(info_page),
                    'text': info_page.text,
                    'page_title': info_page.title}
            result.update(additional_info)
            return result

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
            'page_title': page_title
            }
    if info_page:
        result['text'] = info_page.text

    result.update(additional_info)
    return result


def get_incoming_links(wiki, user, url):
    page = get_page_or_raise(
            wiki, url,
            check_perms=(user, CHECK_FOR_READ),
            fields=['url', 'title', 'meta'])
    links = []
    for link in page.getIncomingLinks():
        try:
            other = get_page_or_raise(
                    wiki, link,
                    check_perms=(user, CHECK_FOR_READ),
                    fields=['url', 'title', 'meta'])
            links.append(get_page_meta(other))
        except PageNotFoundError:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'in_links': links}
    return result


def get_outgoing_links(wiki, user, url):
    page = get_page_or_raise(
            wiki, url,
            check_perms=(user, CHECK_FOR_READ),
            fields=['url', 'title', 'links'])
    links = []
    for link in page.links:
        try:
            other = get_page_or_raise(
                    wiki, link,
                    check_perms=(user, CHECK_FOR_READ),
                    fields=['url', 'title', 'meta'])
            links.append(get_page_meta(other))
        except PageNotFoundError:
            links.append({'url': link, 'missing': True})

    result = {'meta': get_page_meta(page), 'out_links': links}
    return result

