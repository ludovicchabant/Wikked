from wikked import login_manager

class User(object):

    username = ''
    password = ''
    email = ''

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.username)


@login_manager.user_loader
def load_user(userid):
    try:
        return User.objects.get(username=userid)
    except:
        return None
