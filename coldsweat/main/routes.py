import flask
from coldsweat.main import bp


@bp.route('/')
def index():
    return flask.render_template("main/index.html")
