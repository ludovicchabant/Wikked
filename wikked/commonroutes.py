import os.path
from flask import request, abort
from flask_login import current_user
from werkzeug import Response
from werkzeug.wsgi import wrap_file
from wikked.web import app, get_wiki
from wikked.webimpl import (
    get_page_or_raise, url_from_viewarg, mimetype_map)


@app.route('/pagefiles/<path:url>')
def read_pagefile(url):
    wiki = get_wiki()
    user = current_user.get_id()
    page_url = os.path.dirname(url_from_viewarg(url)).\
        replace('\\', '/').\
        rstrip('/')
    page = get_page_or_raise(wiki, page_url, fields=['path'],
                             check_perms=(user, 'read'))
    # If no exception was thrown, we're good for reading the file.

    path_no_ext, _ = os.path.splitext(page.path)
    file_path = os.path.join(path_no_ext, os.path.basename(url))
    try:
        f = open(file_path, 'rb')
    except OSError:
        abort(404)

    r = Response(wrap_file(request.environ, f), direct_passthrough=True)
    _, ext = os.path.splitext(url)
    r.mimetype = mimetype_map.get(ext, '')
    return r
