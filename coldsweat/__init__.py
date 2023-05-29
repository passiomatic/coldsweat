'''
Coldsweat - RSS aggregator and web reader compatible with the Fever API
'''

__version__ = (0, 10, 0, '')
VERSION_STRING = '%d.%d.%d%s' % __version__

import flask
import flask_login
import coldsweat.models as models
import coldsweat.cli as cli
from .config import Config
from .main.routes import SessionUser
from .main import bp as main_blueprint
from .fever import bp as fever_blueprint

def create_app(config_class=Config):
    app = flask.Flask(__name__)
    app.config.from_object(config_class)
    app.secret_key = 'super secret string'  # Change this!

    # Initialize Flask extensions here
    models.db_wrapper.init_app(app)

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
    app.register_blueprint(main_blueprint)

    # Register Fever API routes
    app.register_blueprint(fever_blueprint)

    # Add CLI support
    cli.add_commands(app)

    return app

