import flask
from coldsweat.fever import bp


@bp.route('/', methods=['GET'])
def index():
    return flask.render_template("fever/index.html")
