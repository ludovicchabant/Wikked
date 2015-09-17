from wikked.utils import get_absolute_url
from wikked.webimpl import (
        CHECK_FOR_READ,
        get_page_meta, get_page_or_raise,
        is_page_readable, get_redirect_target,
        get_or_build_pagelist, get_generic_pagelist_builder,
        CircularRedirectError, RedirectNotFound)


def build_pagelist_view_data(pages, user):
    pages = sorted(pages, key=lambda p: p.url)
    data = [get_page_meta(p) for p in pages if is_page_readable(p, user)]
    result = {'pages': data}
    return result


def generic_pagelist_view(wiki, user, list_name, filter_func, fields=None):
    fields = fields or ['url', 'title', 'meta']
    pages = get_or_build_pagelist(
            wiki,
            list_name,
            get_generic_pagelist_builder(wiki, filter_func, fields),
            fields=fields)
    return build_pagelist_view_data(pages, user)


def get_orphans(wiki, user):
    def builder_func():
        wiki.resolve()

        pages = {}
        rev_links = {}
        for p in wiki.getPages(
                no_endpoint_only=True,
                fields=['url', 'title', 'meta', 'links']):
            pages[p.url] = p
            rev_links[p.url] = 0

            for l in p.links:
                abs_l = get_absolute_url(p.url, l)
                cnt = rev_links.get(abs_l, 0)
                rev_links[abs_l] = cnt + 1

        or_pages = []
        for tgt, cnt in rev_links.items():
            if cnt == 0:
                or_pages.append(pages[tgt])
        return or_pages

    fields = ['url', 'title', 'meta', 'links']
    pages = get_or_build_pagelist(wiki, 'orphans', builder_func, fields)
    return build_pagelist_view_data(pages, user)


def get_broken_redirects(wiki, user):
    def filter_func(page):
        redirect_meta = page.getMeta('redirect')
        if redirect_meta is None:
            return False

        path = get_absolute_url(page.url, redirect_meta)
        try:
            target, visited = get_redirect_target(
                    path,
                    fields=['url', 'meta'])
        except CircularRedirectError:
            return True
        except RedirectNotFound:
            return True
        return False

    return generic_pagelist_view(wiki, user, 'broken_redirects', filter_func)


def get_double_redirects(wiki, user):
    def builder_func():
        wiki.resolve()

        pages = {}
        redirs = {}
        for p in wiki.getPages(
                no_endpoint_only=True,
                fields=['url', 'title', 'meta']):
            pages[p.url] = p

            target = p.getMeta('redirect')
            if target:
                target = get_absolute_url(p.url, target)
                redirs[p.url] = target

        dr_pages = []
        for src, tgt in redirs.items():
            if tgt in redirs:
                dr_pages.append(pages[src])
        return dr_pages

    fields = ['url', 'title', 'meta']
    pages = get_or_build_pagelist(wiki, 'double_redirects', builder_func,
                                  fields)
    return build_pagelist_view_data(pages, user)


def get_dead_ends(wiki, user):
    def filter_func(page):
        return len(page.links) == 0

    return generic_pagelist_view(
            wiki, user, 'dead_ends', filter_func,
            fields=['url', 'title', 'meta', 'links'])


def list_pages(wiki, user, url=None):
    pages = list(filter(is_page_readable, wiki.getPages(url)))
    page_metas = [get_page_meta(page) for page in pages]
    result = {'path': url, 'pages': list(page_metas)}
    return result


def get_search_results(wiki, user, query):
    readable_hits = []
    hits = list(wiki.index.search(query))
    for h in hits:
        try:
            get_page_or_raise(wiki, h.url,
                              check_perms=(user, CHECK_FOR_READ))
        except PermissionError:
            continue

        readable_hits.append({
                'url': h.url,
                'title': h.title,
                'text': h.hl_text})

    result = {
            'query': query,
            'hit_count': len(readable_hits),
            'hits': readable_hits}
    return result


def get_search_preview_results(wiki, user, query):
    readable_hits = []
    hits = list(wiki.index.previewSearch(query))
    for h in hits:
        try:
            get_page_or_raise(wiki, h.url,
                              check_perms=(user, CHECK_FOR_READ))
        except PermissionError:
            continue

        readable_hits.append({'url': h.url, 'title': h.title})

    result = {
            'query': query,
            'hit_count': len(readable_hits),
            'hits': readable_hits}
    return result


