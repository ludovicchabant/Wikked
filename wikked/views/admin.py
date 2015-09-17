from flask import request, redirect, render_template
from flask.ext.login import login_user, logout_user
from wikked.web import app, get_wiki


@app.route('/login')
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = request.form.get('remember')
    back_url = request.form.get('back_url')

    wiki = get_wiki()
    user = wiki.auth.getUser(username)
    if user is not None and app.bcrypt:
        if app.bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=bool(remember))
            return redirect(back_url or '/')

    data = {'has_error': True}
    return render_template('login.html', **data)


@app.route('/logout')
def logout():
    logout_user()
    redirect('/')

