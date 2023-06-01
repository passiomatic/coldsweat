import sys
from getpass import getpass
import click
import coldsweat.feed as feed
import coldsweat.models as models
from .models import User


def add_commands(app):

    @app.cli.command("setup")
    def command_setup():
        # @@REMOVEME: use only email instead
        username = 'coldsweat'

        models.setup()

        # Regular setup process. Check if username is already in use
        try:
            User.get(User.username == username)
            raise ValueError(
                'user %s already exists, please select another username with the -u option' % username)
        except User.DoesNotExist:
            pass

        email = input(
            'Enter e-mail for user %s (needed for Fever sync, '
            'hit enter to leave blank): ' % username)
        password = get_password("Enter password for user %s: " % username)

        User.create(username=username, email=email, password=password)
        print("Setup completed for user %s." % username)

    @app.cli.command("fetch")
    def command_fetch():
        feed.fetch_all_feeds()

    @app.cli.command("import")
    @click.argument("filename")
    @click.option('--username', default="coldsweat", help='User to add the subscriptions to')
    # @click.option('--fetch', default=False, help='Fetch subscriptions immediately after add')
    def command_import(username, filename):
        """Import an OPML file and add subscription to given user (default is 'coldsweat' user)."""
        # @@TODO Add fetch option
        fetch_data = False

        user = get_user(username)

        feeds = feed.add_feeds_from_opml(filename)
        for f, g in feeds:
            feed.add_subscription(user, f, g)
        if fetch_data:
            # Fetch only imported feeds
            feed.fetch_feeds([f for f, _ in feeds])

        app.logger.info("import%s completed for user %s."
                        % (' and fetch' if fetch_data else '',
                           user.username))


def get_password(label):

    while True:
        password = read_password(label)
        if not User.validate_password(password):
            print(
                'Error: password should be at least %d characters long'
                % User.MIN_PASSWORD_LENGTH)
            continue
        password_again = read_password("Enter password (again): ")

        if password != password_again:
            print("Error: passwords do not match, please try again")
        else:
            return password


def read_password(prompt_label="Enter password: "):
    if sys.stdin.isatty():
        password = getpass(prompt_label)
    else:
        # Make scriptable by reading password from stdin
        print(prompt_label)
        password = sys.stdin.readline().rstrip()

    return password


def get_user(username):
    try:
        user = User.get(User.username == username)
    except User.DoesNotExist:
        raise ValueError(
            f"unable to find user '{username}'. Please specify a different user or run setup command to create the desired user first")

    return user
