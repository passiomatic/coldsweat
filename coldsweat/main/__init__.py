'''
Web UI blueprint
'''

from flask import Blueprint

bp = Blueprint('main', __name__)

# Make routes importable directly from the blueprint 
from coldsweat.main import routes  # noqa