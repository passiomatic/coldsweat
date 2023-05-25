import coldsweat.feed as feed


def add_commands(app):

    @app.cli.command("fetch")
    def command_fetch():
        feed.fetch_all_feeds()