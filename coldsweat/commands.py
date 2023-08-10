from getpass import getpass
import click
from werkzeug import security
import coldsweat.feed as feed
import coldsweat.models as models
from .models import User


def add_commands(app):

    @app.cli.command("setup", help="Set up a new Coldsweat database and users.")
    @click.argument('email')
    @click.option('-p', '--password',  help=f'Set user password, at least {User.MIN_PASSWORD_LENGTH} characters long')  # noqa
    @click.option('-n', '--name', default="", help='Set user display name')
    @click.option('-r', '--reset-password', is_flag=True, default=False, help='Reset the password for an existing user')  # noqa
    def command_setup(email, password, name, reset_password):
        models.setup()

        user = User.get_or_none(User.email == email)

        if reset_password:
            if user: 
                if password:
                    if validate_password(password):
                        new_password = password
                    else:
                        return                    
                else:
                    new_password = get_password(f"Reset password for user {email}: ")
                user.password_hash = security.generate_password_hash(new_password)      
                user.fever_api_key = User.make_fever_api_key(email, new_password)
                user.save()
                print(f"Password reset for user {email}")
                return
            else:
                print(f'Unknown user {email}')
                return

        if user: 
            print(f'User with email {email} already exists, please use another address')
            return
        
        if password:
            if not validate_password(password):
                return
        else:
            password = get_password(f"Enter password for user {email}: ")

        password_hash = security.generate_password_hash(password)
        fever_api_key = User.make_fever_api_key(email, password)
        User.create(email=email, password_hash=password_hash, fever_api_key=fever_api_key, display_name=name)
        print(f"Setup completed for user {email}")


    @app.cli.command("fetch", help="Update all feeds.")
    def command_fetch():
        feed.fetch_all_feeds()

    @app.cli.command("import", help="Import an OPML file for given user.")
    @click.argument("filename")
    @click.argument("email")
    @click.option('-f', '--fetch', is_flag=True, default=False, help='Fetch subscriptions immediately after import')
    def command_import(filename, email, fetch):
        '''
        Import an OPML file and add subscription to given user
        '''
        try:
            user = User.get(User.email == email)
        except User.DoesNotExist:
            print(f"Unable to find user with email {email}. Please specify a different user or run setup command to create the desired user first")
            return

        feeds = feed.add_feeds_from_opml(filename)
        for f, g in feeds:
            feed.add_subscription(user, f, g)
        if fetch:
            # Fetch only imported feeds
            feed.fetch_feeds([f for f, _ in feeds])

        app.logger.info("import%s completed for user %s."
                        % (' and fetch' if fetch else '',
                           user.email))

def validate_password(password):
    valid = User.validate_password(password)
    if not valid:
        print(f'Error: password should be at least {User.MIN_PASSWORD_LENGTH} characters long')
    return valid

def get_password(label):
    '''
    Get password from stdin
    '''

    while True:
        password = getpass(label)
        if not validate_password(password):
            continue
        password_again = getpass("Enter password (again): ")

        if password != password_again:
            print("Error: passwords do not match, please try again")
        else:
            return password
