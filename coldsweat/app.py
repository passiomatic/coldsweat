import flask
import flask_login
import coldsweat.models as models
import coldsweat.cli as cli
from .config import Config


def create_app(config_class=Config):
    app = flask.Flask(__name__)
    # app.config.from_object(config_class)
    app.secret_key = 'super secret string'  # Change this!

    # Initialize Flask extensions here

    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)

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

    # Register main app routes
    from coldsweat.main import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    # Register Fever API routes
    from coldsweat.fever import bp as fever_blueprint
    app.register_blueprint(fever_blueprint)

    # Add CLI support
    cli.add_commands(app)

    @app.before_request
    def before_request():
        models.database.connect(reuse_if_open=True)

    @app.after_request
    def after_request(response):
        models.database.close()
        return response

    return app


# ---------
# Setup template filters and context
# ---------


# @app.template_filter("human_date")
# def human_date(value):
#     return value.strftime("%b %d, %Y")


# @app.template_filter("human_date_time")
# def human_date(value):
#     return value.strftime("%b %d, %Y at %H:%M")

# @app.context_processor
# def inject_template_vars():
#     return {
#         "last_sync": models.get_last_log(),
#         "nav_tags": get_nav_tags(MAX_TOP_TAGS)
#     }

# ---------
# User auth
# ---------

class SessionUser(flask_login.UserMixin):
    pass


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if flask.request.method == 'GET':
#         return '''
#                <form action='login' method='POST'>
#                 <input type='email' name='email' id='email' value="andrea@passiomatic.com" placeholder='email'/>
#                 <input type='text' name='password' value="password" id='password' placeholder='password'/>
#                 <input type='submit' name='submit'/>
#                </form>
#                '''

#     email = flask.request.form['email']
#     password = flask.request.form['password']
#     user = models.User.validate_credentials(email, password)
#     if user:
#         session_user = SessionUser()
#         session_user.id = email
#         flask_login.login_user(session_user)
#         return flask.redirect(flask.url_for('protected'))

#     return 'Bad login'


# @app.route('/logout')
# def logout():
#     flask_login.logout_user()
#     return 'Logged out'


# @app.route('/protected')
# @flask_login.login_required
# def protected():
#     return 'Logged in as: ' + flask_login.current_user.id


# if __name__ == '__main__':
#     app.run(debug=True)
