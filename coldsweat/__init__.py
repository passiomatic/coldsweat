'''
Coldsweat - RSS aggregator and web reader compatible with the Fever API
'''
__version__ = (0, 10, 2, '')

import os 
import flask_login
import flask
from flask.cli import FlaskGroup
import click
from flask_cdn import CDN
from .auth import bp as auth_blueprint
from .main import bp as main_blueprint
from .fever import bp as fever_blueprint
from .auth import SessionUser
import coldsweat.commands as commands
import coldsweat.models as models

try:
    import tomllib as toml  # Python 3.11+
except ImportError:
    import tomli as toml

cdn = CDN()

class TestingConfig(object):
    DATABASE_URL = 'sqlite:///:memory:'   
    TESTING = True
    
def create_app(config_class=None):
    app = flask.Flask(__name__, instance_relative_config=True)
    # Create an instance dir if needed
    os.makedirs(app.instance_path, exist_ok=True)
    app.logger.debug(f"Flask instance_path is {app.instance_path}")

    if config_class:    
        app.config.from_object(config_class)
    else:
        if app.config.from_file("config.toml", load=toml.load, text=False, silent=True):
            app.logger.info(f"Using config.toml file found in {app.instance_path}")
        else:
            # Attempt to load settings from env. vars
            app.config.from_prefixed_env()

        if 'DATABASE_URL' in app.config:
            app.logger.info(f"Using DATABASE_URL {app.config['DATABASE_URL']}")
        else:
            # Fallback to sqlite db and dev secret key
            default_database_url = f"sqlite:///{os.path.join(app.instance_path, 'coldsweat.db')}"
            #@@TODO Specify foreign_keys=1 journal_mode=WAL"
            app.logger.debug(f"DATABASE_URL not found in configuration settings, using default {default_database_url}")
            app.config['SECRET_KEY'] = "Secret key for dev purposes only"
            app.config['DATABASE_URL'] = default_database_url

    # Initialize Flask extensions here
    
    cdn.init_app(app)
    
    models.db_wrapper.init_app(app)
    if models.db_wrapper.get_engine() == 'sqlite':
        models.db_wrapper.database.pragma('foreign_keys', 1, permanent=True)
        models.db_wrapper.database.pragma('journal_mode', 'wal', permanent=True)

    login_manager = flask_login.LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def user_loader(user_id):
        user = models.User.get_or_none(models.User.id == int(user_id))
        if not user:
            return None

        return SessionUser(user)

    # @@TODO Use for API auth 
    # @login_manager.request_loader
    # def request_loader(request):
    #     email = request.form.get('email')
    #     user = models.User.get_or_none(email=email)
    #     if not user:
    #         return None

    #     return SessionUser(user)

    # Register auth routes
    app.register_blueprint(auth_blueprint)

    # Register main app routes
    app.register_blueprint(main_blueprint)

    # Register Fever API routes
    app.register_blueprint(fever_blueprint)

    # Add CLI support
    commands.add_commands(app)

    with app.app_context():
        from . import filters  # noqa

    return app

@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """Management script for the Coldsweat application."""