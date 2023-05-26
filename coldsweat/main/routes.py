import flask
import flask_login
import coldsweat.models as models
from coldsweat.main import bp


@bp.route('/')
def index():
    return flask.render_template("main/index.html")


@bp.route('/protected')
@flask_login.login_required
def protected():
    return f'Logged in as: {flask_login.current_user.id}' 


# ---------
# User auth
# ---------

class SessionUser(flask_login.UserMixin):
    pass


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return flask.render_template("login.html") 

    email = flask.request.form['email']
    password = flask.request.form['password']
    user = models.User.validate_credentials(email, password)
    if user:
        session_user = SessionUser()
        session_user.id = email
        flask_login.login_user(session_user)
        return flask.redirect(flask.url_for('main.protected'))

    return 'Bad login'


@bp.route('/logout')
def logout():
    flask_login.logout_user()
    return 'Logged out'
