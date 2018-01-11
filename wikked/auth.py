import re
import logging


logger = logging.getLogger(__name__)


# Page permissions.
PERM_NONE = 0
PERM_READ = 2**0
PERM_EDIT = 2**1
PERM_CREATE = 2**2
PERM_DELETE = 2**3
PERM_HISTORY = 2**4
PERM_REVERT = 2**5
PERM_SEARCH = 2**6
PERM_UPLOAD = 2**7
# Site-wide premissions.
PERM_INDEX = 2**8
PERM_LIST = 2**9
PERM_LISTREFRESH = 2**10
PERM_WIKIHISTORY = 2**11
PERM_WIKIUPLOAD = 2**12
PERM_USERS = 2**13

PERM_NAMES = {
        # Page permissions.
        'none': PERM_NONE,
        'read': PERM_READ,
        'edit': PERM_EDIT,
        'create': PERM_CREATE,
        'delete': PERM_DELETE,
        'history': PERM_HISTORY,
        'revert': PERM_REVERT,
        'search': PERM_SEARCH,
        'upload': PERM_UPLOAD,
        # Site-wide permissions.
        'index': PERM_INDEX,
        'list': PERM_LIST,
        'listrefresh': PERM_LISTREFRESH,
        'wikihistory': PERM_WIKIHISTORY,
        'wikiupload': PERM_WIKIUPLOAD,
        'users': PERM_USERS,
        # Aliases
        'write': PERM_EDIT,
        'all': 0xffff
        }

ANONYMOUS_USERNAME = 'anonymous'
ALL_USERS_GROUP = '*'

DEFAULT_USER_ROLES = {
        'reader': (PERM_READ | PERM_HISTORY),
        'contributor': (PERM_READ | PERM_EDIT | PERM_HISTORY | PERM_UPLOAD),
        'editor': (PERM_READ | PERM_EDIT | PERM_CREATE | PERM_DELETE |
                   PERM_HISTORY | PERM_REVERT | PERM_UPLOAD | PERM_WIKIUPLOAD),
        'admin': 0xffff
        }


class User:
    """ A user with an account on the wiki.
    """
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.permissions = PERM_NONE
        self.groups = []

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.username)


class NoSuchGroupOrUserError(Exception):
    pass


class MultipleGroupMembershipError(Exception):
    pass


class CyclicUserGroupError(Exception):
    pass


class InvalidPermissionError(Exception):
    pass


class _UserInfo:
    def __init__(self, password):
        self.password = password
        self.allows = PERM_NONE
        self.denies = PERM_NONE
        self.group_name = None
        self.flattened_perms = PERM_NONE
        self.flattened_lineage = None


class _UserGroupInfo:
    def __init__(self):
        self.allows = PERM_NONE
        self.denies = PERM_NONE
        self.parent_group_name = None


class _UserRoleInfo:
    def __init__(self):
        self.allows = PERM_NONE
        self.denies = PERM_NONE


re_sep = re.compile(r'[,;]')


def _parse_permission(perm):
    # 'perm' or '+perm' means 'allows'. '-perm' means 'denies'.
    is_allow = True
    if perm[0] == '-':
        perm = perm[1:]
        is_allow = False

    p_bit = PERM_NAMES.get(perm)
    if p_bit is not None:
        return p_bit, is_allow
    raise InvalidPermissionError(perm)


def _parse_permission_list(permlist):
    perms = [p.strip() for p in re_sep.split(permlist)]
    allows = PERM_NONE
    denies = PERM_NONE
    for p in perms:
        p_bit, is_allow = _parse_permission(p)
        if is_allow:
            allows |= p_bit
        else:
            denies |= p_bit
    return allows, denies


def parse_config(config, roles, groups, users):
    member_map = {}

    # Pre-populate the default roles, and then read the user-defined
    # list of roles.
    for name, bits in DEFAULT_USER_ROLES.items():
        ri = _UserRoleInfo()
        ri.allows = bits
        roles[name] = ri
    if config.has_section('roles'):
        for role in config.items('roles'):
            ri = _UserRoleInfo()
            ri.allows, ri.denies = _parse_permission_list(role[1])
            roles[role[0]] = ri

    # Get the list of groups.
    if config.has_section('groups'):
        for group in config.items('groups'):
            # Just create the group for now, and store members in a temp
            # map, because some members might only be declared later.
            groups[group[0]] = _UserGroupInfo()
            member_map[group[0]] = [m.strip() for m in re_sep.split(group[1])]

    # Get the list of users and passwords.
    if config.has_section('users'):
        for user in config.items('users'):
            users[user[0]] = _UserInfo(user[1])

    # Now resolve group membership -- we should have all the users
    # and groups known at this point.
    for name, members in member_map.items():
        for m in members:
            # Is it a user?
            u = users.get(m)
            if u is not None:
                if u.group_name is not None:
                    raise MultipleGroupMembershipError(
                            "User '%s' can't be added to group '%s' "
                            "because it already belongs to group '%s'." %
                            (m, name, u.group_name))
                u.group_name = name
                continue

            # Is it a group then?
            g = groups.get(m)
            if g is not None:
                if g.parent_group_name is not None:
                    raise MultipleGroupMembershipError(
                            "Group '%s' can't be added to group '%s' "
                            "because it already belongs to group '%s'." %
                            (m, name, g.parent_group_name))
                g.parent_group_name = name
                continue

            # Can't find it!
            raise NoSuchGroupOrUserError(m)

    # Add entries for "all known users" and "anonymous users".
    # Those are potentially referenced in the 'permissions' section to
    # assign broad access levels.
    users[ANONYMOUS_USERNAME] = _UserInfo(None)
    groups[ALL_USERS_GROUP] = _UserGroupInfo()

    # Assign permissions.
    if config.has_section('permissions'):
        for perm in config.items('permissions'):
            # Get the user or group subject.
            subj = users.get(perm[0])
            if subj is None:
                subj = groups.get(perm[0])
                if subj is None:
                    raise NoSuchGroupOrUserError(perm[0])

            # Get the permission/role list.
            allows = PERM_NONE
            denies = PERM_NONE
            perms = [p.strip() for p in re_sep.split(perm[1])]
            for p in perms:
                # If it's a role, just combine its allow/deny lists.
                role = roles.get(p)
                if role is not None:
                    allows |= role.allows
                    denies |= role.denies
                    continue

                # Otherwise, parse actual permissions as usual.
                p_bit, is_allow = _parse_permission(p)
                if is_allow:
                    allows |= p_bit
                else:
                    denies |= p_bit
            subj.allows |= allows
            subj.denies |= denies
    else:
        # No permissions specified... use the defaults.
        users[ANONYMOUS_USERNAME].allows = DEFAULT_USER_ROLES['admin']
        groups[ALL_USERS_GROUP].allows = DEFAULT_USER_ROLES['admin']

    # Flatten user permissions so we don't have to go through the tree
    # all the time, and so we can detect cyclic problems right away.
    for username, user_info in users.items():
        group_lineage = _get_group_lineage(user_info, groups)
        if username != ANONYMOUS_USERNAME:
            group_lineage.append(ALL_USERS_GROUP)
        # Walk the lineage the other way, i.e. from the root group down
        # to the user itself.
        user_info.flattened_lineage = list(reversed(group_lineage))
        for gn in user_info.flattened_lineage:
            ginfo = groups[gn]
            user_info.flattened_perms |= ginfo.allows
            user_info.flattened_perms &= ~ginfo.denies
        user_info.flattened_perms |= user_info.allows
        user_info.flattened_perms &= ~user_info.denies


def _get_group_lineage(user_info, groups):
    lineage = []
    if user_info.group_name is not None:
        _do_get_group_lineage(groups, user_info.group_name, lineage)
    return lineage


def _do_get_group_lineage(groups, group_name, lineage):
    # Check cycles.
    if group_name in lineage:
        raise CyclicUserGroupError("Group '%s' is in a parenting cycle: %s" %
                                   (group_name, ' -> '.join(lineage)))
    # Check existence.
    group_info = groups.get(group_name)
    if group_info is None:
        raise NoSuchGroupOrUserError(group_name)

    # Yep, it's all good. Add the group to the lineage, and keep walking
    # up the parent chain.
    lineage.append(group_name)
    if group_info.parent_group_name:
        _do_get_group_lineage(groups, group_info.parent_group_name, lineage)


re_page_acl = re.compile(r'^(?P<name>[^\s]+)\s*\=\s*(?P<perms>.*)$')


class UserManager:
    """ A class that keeps track of users and their permissions.
    """
    def __init__(self, config):
        self._roles = {}
        self._groups = {}
        self._users = {}
        parse_config(config, self._roles, self._groups, self._users)

    def start(self, wiki):
        pass

    def init(self, wiki):
        pass

    def postInit(self):
        pass

    def getUsers(self):
        for name, info in self._users.items():
            yield self._createUser(name, info)

    def getUserNames(self):
        return self._users.keys()

    def getUser(self, username):
        info = self._users.get(username)
        if info is not None:
            return self._createUser(username, info)
        return None

    def getGroupNames(self):
        return self._groups.keys()

    def hasPagePermission(self, page, username, perm):
        extra_acl = None
        page_perms = page.getLocalMeta('acl')
        if page_perms is not None:
            extra_acl = []
            for pp in page_perms:
                m = re_page_acl.match(pp)
                if m:
                    name = m.group('name')
                    perms = [p.strip()
                             for p in re_sep.split(m.group('perms'))]
                    extra_acl.append((name, perms))

        return self.hasPermission(username, perm, extra_acl)

    def hasPermission(self, username, perm, extra_acl=None):
        username = username or ANONYMOUS_USERNAME
        user_info = self._users.get(username)
        if user_info is None:
            raise NoSuchGroupOrUserError(username)

        # Start with the user permissions, and patch them with whatever
        # extra permissions specify.
        effective_perms = user_info.flattened_perms
        if extra_acl is not None:
            for name, perms in extra_acl:
                if (name == username or
                        name in user_info.flattened_lineage):
                    for p in perms:
                        if p[0] == '+':
                            # Add permission.
                            p_bit = self._getPermissions(p[1:])
                            effective_perms |= p_bit
                        elif p[0] == '-':
                            # Remove permission.
                            p_bit = self._getPermissions(p[1:])
                            effective_perms &= ~p_bit
                        else:
                            # Replace permissions.
                            p_bit = self._getPermissions(p)
                            effective_perms = p_bit

        # Test the effective permissions now!
        return (effective_perms & perm) != 0

    def _getPermissions(self, perm_or_role):
        role_info = self._roles.get(perm_or_role)
        if role_info is not None:
            return (role_info.allows & ~role_info.denies)
        p_bit = PERM_NAMES.get(perm_or_role)
        if p_bit is not None:
            return p_bit
        raise InvalidPermissionError(
            "'%s' is not a valid permission or role." % perm_or_role)

    def _createUser(self, name, info):
        u = User(name, info.password)
        u.permissions = info.flattened_perms
        u.groups += info.flattened_lineage
        return u
