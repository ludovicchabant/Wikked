import logging


class User(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.groups = []

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.username)

    def is_admin(self):
        return 'administrators' in self.groups


class UserManager(object):
    def __init__(self, config, logger=None):
        if logger is None:
            logger = logging.getLogger('wikked.auth')
        self.logger = logger
        self._updateUserInfos(config)

    def getUsers(self):
        for user in self.users:
            yield self._createUser(user)

    def getUser(self, username):
        for user in self.users:
            if user['username'] == username:
                return self._createUser(user)
        return None

    def _updateUserInfos(self, config):
        self.users = []
        if config.has_section('users'):
            groups = []
            if config.has_section('groups'):
                groups = config.items('groups')

            for user in config.items('users'):
                user_info = { 'username': user[0], 'password': user[1], 'groups': [] }
                for group in groups:
                    users_in_group = [u.strip() for u in group[1].split(',')]
                    if user[0] in users_in_group:
                        user_info['groups'].append(group[0])
                self.users.append(user_info)

    def _createUser(self, user_info):
        user = User(user_info['username'], user_info['password'])
        user.groups = list(user_info['groups'])
        return user

