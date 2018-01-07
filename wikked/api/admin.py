from flask import jsonify
from wikked.web import app, get_wiki
from wikked.webimpl.decorators import requires_permission


@app.route('/api/admin/reindex', methods=['POST'])
@requires_permission('index')
def api_admin_reindex():
    wiki = get_wiki()
    wiki.index.reset(wiki.getPages())
    result = {'ok': 1}
    return jsonify(result)
