import pytest
from configparser import SafeConfigParser
from wikked.auth import (
        UserManager, PERM_NAMES,
        NoSuchGroupOrUserError, MultipleGroupMembershipError,
        CyclicUserGroupError, InvalidPermissionError)


def _user_manager_from_str(txt):
    config = SafeConfigParser()
    config.read_string(txt)
    return UserManager(config)


def _p(name):
    return PERM_NAMES[name]


def test_empty_auth():
    m = _user_manager_from_str("")
    assert list(m.getUserNames()) == ['anonymous']
    assert list(m.getGroupNames()) == ['*']


def test_missing_user1():
    with pytest.raises(NoSuchGroupOrUserError):
        m = _user_manager_from_str("""
[permissions]
dorothy = read
""")


def test_missing_user2():
    with pytest.raises(NoSuchGroupOrUserError):
        m = _user_manager_from_str("""
[groups]
mygroup = dorothy
""")


def test_multiple_group_membership1():
    with pytest.raises(MultipleGroupMembershipError):
        m = _user_manager_from_str("""
[users]
dorothy = pass
[groups]
one = dorothy
two = dorothy
""")


def test_multiple_group_membership2():
    with pytest.raises(MultipleGroupMembershipError):
        m = _user_manager_from_str("""
[users]
dorothy = pass
[groups]
one = dorothy
two = one
three = one
""")


def test_auth1():
    m = _user_manager_from_str("""
[users]
dorothy = pass
[permissions]
dorothy = read,edit
""")
    assert m.hasPermission('dorothy', _p('read'))
    assert m.hasPermission('dorothy', _p('edit'))
    assert not m.hasPermission('dorothy', _p('create'))


def test_auth2():
    m = _user_manager_from_str("""
[users]
dorothy = pass
toto = pass
tinman = pass
[groups]
humans = dorothy
others = toto, tinman
[permissions]
humans = read,edit
others = read
tinman = create
""")
    assert m.hasPermission('dorothy', _p('read'))
    assert m.hasPermission('dorothy', _p('edit'))
    assert not m.hasPermission('dorothy', _p('create'))
    assert m.hasPermission('toto', _p('read'))
    assert not m.hasPermission('toto', _p('edit'))
    assert not m.hasPermission('toto', _p('create'))
    assert m.hasPermission('tinman', _p('read'))
    assert not m.hasPermission('tinman', _p('edit'))
    assert m.hasPermission('tinman', _p('create'))
