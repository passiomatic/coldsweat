from datetime import datetime, date, timezone, timedelta
# from pathlib import Path
# from operator import attrgetter
# from itertools import groupby, islice
import flask
from peewee import *
import coldsweat.models as models

app = flask.Flask(__name__)


@app.before_request
def before_request():
    models.connect()


@app.after_request
def after_request(response):
    models.close()
    return response

# ---------
# Setup template filters and context
# ---------


@app.template_filter("human_date")
def human_date(value):
    return value.strftime("%b %d, %Y")


@app.template_filter("human_date_time")
def human_date(value):
    return value.strftime("%b %d, %Y at %H:%M")

# @app.context_processor
# def inject_template_vars():
#     return {
#         "last_sync": models.get_last_log(),
#         "nav_tags": get_nav_tags(MAX_TOP_TAGS)
#     }

# ---------
# Home
# ---------


@app.route('/')
def home():
    return flask.render_template("index.html")
