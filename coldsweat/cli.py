from getpass import getpass
import click
import coldsweat.feed as feed
import coldsweat.models as models
from .models import User


def add_commands(app):

    @app.cli.command("setup")
    @click.argument('email')
    @click.option('-p', '--password',  help=f'User password, at least {User.MIN_PASSWORD_LENGTH} characters long)')  # noqa
    @click.option('-n', '--name', default="", help='User display name')
    def command_setup(email, password, name):
        models.setup()

        try:
            User.get(User.email == email)
            raise ValueError(
                f'user with email {email} already exists, please use another one')
        except User.DoesNotExist:
            pass

        # @@TODO Check password length
        if not password:
            password = get_password(f"Enter password for user {email}: ")

        # @@REMOVEME: use only email instead
        # @@TODO: pass display name
        User.create(username=email, email=email, password=password)
        print(f"Setup completed for {email}")

    @app.cli.command("fetch")
    def command_fetch():
        feed.fetch_all_feeds()

    @app.cli.command("import")
    @click.argument("filename")
    @click.argument("email")
    @click.option('--fetch', default=False, help='Fetch subscriptions immediately after add')
    def command_import(filename, email, fetch):
        """Import an OPML file and add subscription to given user"""
        # @@TODO Add fetch option
        fetch_data = False

        user = User.get(User.email == email)

        feeds = feed.add_feeds_from_opml(filename)
        for f, g in feeds:
            feed.add_subscription(user, f, g)
        if fetch_data:
            # Fetch only imported feeds
            feed.fetch_feeds([f for f, _ in feeds])

        app.logger.info("import%s completed for user %s."
                        % (' and fetch' if fetch_data else '',
                           user.email))


def get_password(label):
    '''
    Get password from stdin
    '''

    while True:
        password = getpass(label)
        if not User.validate_password(password):
            print(
                'Error: password should be at least %d characters long'
                % User.MIN_PASSWORD_LENGTH)
            continue
        password_again = getpass("Enter password (again): ")

        if password != password_again:
            print("Error: passwords do not match, please try again")
        else:
            return password


def get_user(username):
    try:
        user = User.get(User.username == username)
    except User.DoesNotExist:
        raise ValueError(
            f"unable to find user '{username}'. Please specify a different user or run setup command to create the desired user first")

    return user
