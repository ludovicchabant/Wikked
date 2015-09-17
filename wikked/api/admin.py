from flask import jsonify, abort, request
from flask.ext.login import logout_user, current_user
from wikked.web import app, get_wiki, login_manager
from wikked.webimpl.admin import do_login_user


@app.route('/api/admin/reindex', methods=['POST'])
def api_admin_reindex():
    if not current_user.is_authenticated() or not current_user.is_admin():
        return login_manager.unauthorized()
    wiki = get_wiki()
    wiki.index.reset(wiki.getPages())
    result = {'ok': 1}
    return jsonify(result)


@app.route('/api/user/login', methods=['POST'])
def api_user_login():
    if do_login_user():
        username = request.form.get('username')
        result = {'username': username, 'logged_in': 1}
        return jsonify(result)
    abort(401)


@app.route('/api/user/is_logged_in')
def api_user_is_logged_in():
    if current_user.is_authenticated():
        result = {'logged_in': True}
        return jsonify(result)
    abort(401)


@app.route('/api/user/logout', methods=['POST'])
def api_user_logout():
    logout_user()
    result = {'ok': 1}
    return jsonify(result)


@app.route('/api/user/info')
def api_current_user_info():
    user = current_user
    if user.is_authenticated():
        result = {
                'user': {
                    'username': user.username,
                    'groups': user.groups
                    }
                }
        return jsonify(result)
    return jsonify({'user': False})


@app.route('/api/user/info/<name>')
def api_user_info(name):
    wiki = get_wiki()
    user = wiki.auth.getUser(name)
    if user is not None:
        result = {
                'user': {
                    'username': user.username,
                    'groups': user.groups
                    }
                }
        return jsonify(result)
    abort(404)


