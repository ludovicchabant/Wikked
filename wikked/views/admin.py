import urllib.parse
from flask import url_for, render_template
from wikked.views import add_auth_data, add_navigation_data
from wikked.web import app, get_wiki
from wikked.webimpl.decorators import requires_permission


@app.route('/special/users')
@requires_permission('users')
def special_users():
    wiki = get_wiki()

    users = []
    for user in wiki.auth.getUsers():
        user_url = 'user:/%s' % urllib.parse.quote(user.username.title())
        users.append({
            'username': user.username,
            'url': url_for('read', url=user_url),
            'groups': list(user.groups)
        })

    data = {
        'title': "Users",
        'users': users}
    add_auth_data(data)
    add_navigation_data(None, data)

    return render_template('special-users.html', **data)
