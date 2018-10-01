import functools
from flask_login import current_user
from wikked.auth import PERM_NAMES
from wikked.web import get_wiki
from wikked.webimpl import UserPermissionError


def requires_permission(perm):
    if isinstance(perm, str):
        perm = [perm]

    p_bit = 0
    for p in perm:
        p_bit |= PERM_NAMES[p]

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            wiki = get_wiki()
            if not wiki.auth.hasPermission(current_user.get_id(), p_bit):
                raise UserPermissionError(
                    perm, "You don't have permission for this.")
            return f(*args, **kwargs)
        return wrapper
    return decorator
