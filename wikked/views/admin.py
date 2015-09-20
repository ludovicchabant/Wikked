from flask import request, redirect, render_template
from flask.ext.login import login_user, logout_user, current_user
from wikked.views import add_auth_data, add_navigation_data
from wikked.web import app, get_wiki


@app.route('/login', methods=['GET', 'POST'])
def login():
    wiki = get_wiki()

    data = {}
    add_auth_data(data)
    add_navigation_data(
            None, data,
            raw_url='/api/user/login')

    if request.method == 'GET':
        if current_user.is_authenticated():
            data['already_logged_in'] = True
            return render_template('logout.html', **data)
        else:
            return render_template('login.html', **data)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')
        back_url = request.form.get('back_url')

        user = wiki.auth.getUser(username)
        if user is not None and app.bcrypt:
            if app.bcrypt.check_password_hash(user.password, password):
                login_user(user, remember=bool(remember))
                return redirect(back_url or '/')

        data['has_error'] = True
        return render_template('login.html', **data)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'GET':
        data = {}
        add_auth_data(data)
        add_navigation_data(
                None, data,
                raw_url='/api/user/logout')
        return render_template('logout.html', **data)

    if request.method == 'POST':
        logout_user()
        return redirect('/')

