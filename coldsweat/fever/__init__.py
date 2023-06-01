'''
Fever API blueprint
'''

from flask import Blueprint

bp = Blueprint('fever', __name__, url_prefix='/fever')

# Make routes importable directly from the blueprint
from coldsweat.fever import routes
