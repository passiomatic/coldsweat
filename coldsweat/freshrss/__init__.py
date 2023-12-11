'''
A Google Reader-like API
'''

from flask import Blueprint

bp = Blueprint('freshrss', __name__, url_prefix='/freshrss')

# Make routes importable directly from the blueprint 
from coldsweat.freshrss import routes  # noqa