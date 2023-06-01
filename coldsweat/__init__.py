'''
Coldsweat - RSS aggregator and web reader compatible with the Fever API
'''
__version__ = (0, 10, 0, '')
VERSION_STRING = '%d.%d.%d%s' % __version__

from .auth import bp as auth_blueprint
from .main import bp as main_blueprint
from .fever import bp as fever_blueprint
from .auth import SessionUser
from .config import Config
import coldsweat.cli as cli
import coldsweat.models as models
import flask_login
import flask


def create_app(config_class=Config):
    app = flask.Flask(__name__)
    app.config.from_object(config_class)
    app.secret_key = 'super secret string'  # Change this!

    # Initialize Flask extensions here
    models.db_wrapper.init_app(app)

    login_manager = flask_login.LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def user_loader(user_id):
        user = models.User.get_or_none(user_id)
        if not user:
            return None

        return SessionUser(user)

    @login_manager.request_loader
    def request_loader(request):
        email = request.form.get('email')
        user = models.User.get_or_none(email=email)
        if not user:
            return None

        return SessionUser(user)

    # Register auth routes
    app.register_blueprint(auth_blueprint)

    # Register main app routes
    app.register_blueprint(main_blueprint)

    # Register Fever API routes
    app.register_blueprint(fever_blueprint)

    # Add CLI support
    cli.add_commands(app)

    with app.app_context():
        from . import filters  # noqa

    return app