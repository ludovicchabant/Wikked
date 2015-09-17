from flask import request
from flask.ext.login import login_user
from wikked.web import app, get_wiki


def do_login_user():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = request.form.get('remember')

    wiki = get_wiki()
    user = wiki.auth.getUser(username)
    if user is not None and app.bcrypt:
        if app.bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=bool(remember))
            return True
    return False

