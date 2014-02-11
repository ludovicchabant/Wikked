from flask import g, jsonify, abort, request
from flask.ext.login import login_user, logout_user, current_user
from wikked.web import app, login_manager


@app.route('/api/admin/reindex', methods=['POST'])
def api_admin_reindex():
    if not current_user.is_authenticated() or not current_user.is_admin():
        return login_manager.unauthorized()
    g.wiki.index.reset(g.wiki.getPages())
    result = {'ok': 1}
    return jsonify(result)


@app.route('/api/user/login', methods=['POST'])
def api_user_login():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = request.form.get('remember')

    user = g.wiki.auth.getUser(username)
    if user is not None and app.bcrypt:
        if app.bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=bool(remember))
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
    user = g.wiki.auth.getUser(name)
    if user is not None:
        result = {
                'user': {
                    'username': user.username,
                    'groups': user.groups
                    }
                }
        return jsonify(result)
    abort(404)

