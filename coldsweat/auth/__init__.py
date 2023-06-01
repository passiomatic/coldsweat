'''
Auth blueprint
'''

from flask import Blueprint
import flask_login

bp = Blueprint('auth', __name__, template_folder='templates')

class SessionUser(flask_login.UserMixin):
    '''
    A user in the urrent web session. We cannot mix model.User with 
      flask_login.UserMixin due to methdod names clashing.
    '''

    def __init__(self, user):
        self.id = user.id
        # TODO: Use display_name
        self.display_name = user.username

# Make routes importable directly from the blueprint
from coldsweat.auth import routes

