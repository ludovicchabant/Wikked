import re
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
        self._updatePermissions(config)
        self._updateUserInfos(config)

    def getUsers(self):
        for user in self._users:
            yield self._createUser(user)

    def getUser(self, username):
        for user in self._users:
            if user['username'] == username:
                return self._createUser(user)
        return None

    def isPageReadable(self, page, username):
        return self._isAllowedForMeta(page, 'readers', username)

    def isPageWritable(self, page, username):
        return self._isAllowedForMeta(page, 'writers', username)

    def _isAllowedForMeta(self, page, meta_name, username):
        if (self._permissions[meta_name] is not None and 
                username not in self._permissions[meta_name]):
            return False
        if meta_name in page.all_meta['user']:
            allowed = [r.strip() for r in re.split(r'[ ,;]', page.all_meta['user'][meta_name])]
            if username is None:
                return 'anonymous' in allowed
            else:
                return '*' in allowed or username in allowed
        return True

    def _updatePermissions(self, config):
        self._permissions = {
                'readers': None,
                'writers': None
                }
        if config.has_option('permissions', 'readers'):
            self._permissions['readers'] = [p.strip() for p in re.split(r'[ ,;]', config.get('permissions', 'readers'))]
        if config.has_option('permissions', 'writers'):
            self._permissions['writers'] = [p.strip() for p in re.split(r'[ ,;]', config.get('permissions', 'writers'))]

    def _updateUserInfos(self, config):
        self._users = []
        if config.has_section('users'):
            groups = []
            if config.has_section('groups'):
                groups = config.items('groups')

            for user in config.items('users'):
                user_info = { 'username': user[0], 'password': user[1], 'groups': [] }
                for group in groups:
                    users_in_group = [u.strip() for u in re.split(r'[ ,;]', group[1])]
                    if user[0] in users_in_group:
                        user_info['groups'].append(group[0])
                self._users.append(user_info)

    def _createUser(self, user_info):
        user = User(user_info['username'], user_info['password'])
        user.groups = list(user_info['groups'])
        return user

