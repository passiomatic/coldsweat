from datetime import datetime, date, timezone, timedelta
# from pathlib import Path
# from operator import attrgetter
# from itertools import groupby, islice
import flask
import flask_login
from peewee import *
import coldsweat.models as models

app = flask.Flask(__name__)
app.secret_key = 'super secret string'  # Change this!


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
# User auth
# ---------

login_manager = flask_login.LoginManager()
login_manager.init_app(app)


class SessionUser(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    if not models.User.get_or_none(email=email):
        return

    user = SessionUser()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if not models.User.get_or_none(email=email):
        return

    user = SessionUser()
    user.id = email
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return '''
               <form action='login' method='POST'>
                <input type='email' name='email' id='email' value="andrea@passiomatic.com" placeholder='email'/>
                <input type='text' name='password' value="password" id='password' placeholder='password'/>
                <input type='submit' name='submit'/>
               </form>
               '''

    email = flask.request.form['email']
    password = flask.request.form['password']
    user = models.User.validate_credentials(email, password)
    if user:
        session_user = SessionUser()
        session_user.id = email
        flask_login.login_user(session_user)
        return flask.redirect(flask.url_for('protected'))

    return 'Bad login'


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return 'Logged out'


@app.route('/protected')
@flask_login.login_required
def protected():
    return 'Logged in as: ' + flask_login.current_user.id


# ---------
# Home
# ---------


@app.route('/')
def home():
    return flask.render_template("index.html")
