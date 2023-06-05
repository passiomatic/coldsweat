import flask
import flask_login
from ..models import User
from . import bp, SessionUser


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return flask.render_template("auth/login.html")

    email = flask.request.form['email']
    password = flask.request.form['password']
    user = User.validate_credentials(email, password)
    if user:
        session_user = SessionUser(user)
        flask_login.login_user(session_user)
        return flask.redirect(flask.url_for('main.index'))
    return flask.render_template("auth/login.html")


@bp.route('/logout')
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('main.index'))
