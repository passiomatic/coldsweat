'''
Auth blueprint
'''

from flask import Blueprint
import flask_login

bp = Blueprint('auth', __name__, template_folder='templates')

class SessionUser(flask_login.UserMixin):
    '''
    A user in the current web session. We cannot mix models.User with 
      flask_login.UserMixin due to methdod names clashing, so we wrap it 
      instead
    '''

    def __init__(self, user):
        self.id = user.id
        self.db_user = user

# Make routes importable directly from the blueprint
from coldsweat.auth import routes  # noqa
