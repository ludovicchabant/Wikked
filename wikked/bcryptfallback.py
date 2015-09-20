import logging

logger = logging.getLogger(__name__)

try:
    from flask.ext.bcrypt import Bcrypt, generate_password_hash
except ImportError:
    logger.warning("Bcrypt not available... falling back to SHA512.")
    logger.warning("Run `pip install Flask-Bcrypt` for more secure "
                   "password hashing.")

    import hashlib

    def generate_password_hash(password):
        return hashlib.sha512(password.encode('utf8')).hexdigest()

    def check_password_hash(reference, check):
        check_hash = hashlib.sha512(check.encode('utf8')).hexdigest()
        return check_hash == reference

    class SHA512Fallback(object):
        def __init__(self, app=None):
            self.generate_password_hash = generate_password_hash
            self.check_password_hash = check_password_hash

    Bcrypt = SHA512Fallback

