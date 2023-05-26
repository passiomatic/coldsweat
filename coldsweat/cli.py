import click
import coldsweat.feed as feed
# from coldsweat.models import models
from .models import User


def add_commands(app):

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


def get_user(username):
    try:
        user = User.get(User.username == username)
    except User.DoesNotExist:
        raise ValueError(
            f"unable to find user '{username}'. Please specify a different user or run setup command to create the desired user first")

    return user
