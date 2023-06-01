'''
Database models
'''
import pickle
from datetime import datetime
from playhouse.signals import (pre_save, Model)
from playhouse.flask_utils import FlaskDB
from peewee import (BlobField, BooleanField, CharField, DateTimeField,
                    ForeignKeyField,
                    IntegerField, IntegrityError,
                    TextField)
from passlib import context
from .utilities import datetime_as_epoch, make_md5_hash, make_sha1_hash

__all__ = [
    'User',
    'Group',
    'Feed',
    'Entry',
    'Read',
    'Saved',
    'Subscription',
    'Session',
    'setup',
]

# Feed default icon
_ICON = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAA\
f8/9hAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAUtJREFUeNqk\
089HBGEcx/G2SaeoS0RERJElusbSIUUmsfQHFOm8lyLaUpT+hSKt0l5K2bRESod0LVIs3\
Yuuy5J6f/nM+Japlh5enpl5Zj/z/PhuaiOfb/hPa1KfxTSecYMyXusJaFQ/jFHMYRcvOE\
Om3oArPH0bs8BLHKLjr4Ai+pDCGLZR09gkbpH+LcA3W/8M+nGiZ124TgqJAmztdzhAiAA\
VTGBB77SihPakgLRM4Vhr79bYuguxmWwlBRRwiqruhzSjrAs50nWo8S8BdvbjaMOiNrAF\
e+4oc25jl3/aRHthDSO6btaUAxVZQe9loqONAjrxiA/Mqy5WNNajo7S2rz7QUuIAK+NeX\
a/qy5uunENXcFW38XGAr8KKpl/TD6wNqn/XUqKZxX+mor42gB0XtoQ33LtnOS3p3AdYux\
DfHjCbUKnl6OZTgAEAR+pHH9rWoLkAAAAASUVORK5CYII="

# Pass Peewee Model class with signal support
# See https://docs.peewee-orm.com/en/latest/peewee/playhouse.html#database-wrapper
db_wrapper = FlaskDB(model_class=Model)

# ------------------------------------------------------
# Custom fields
# ------------------------------------------------------


class PickleField(BlobField):

    def db_value(self, value):
        return super(PickleField, self).db_value(pickle.dumps(value, 2))
    # Use newer protocol

    def python_value(self, value):
        return pickle.loads(value)

# ------------------------------------------------------
# Coldsweat models
# ------------------------------------------------------


class User(db_wrapper.Model):
    """
    Coldsweat user
    """

    DEFAULT_USERNAME = 'coldsweat'
    MIN_PASSWORD_LENGTH = 12

    username = CharField(unique=True)
    # display_name = CharField(default='')
    email = CharField(unique=True)
    api_key = CharField(unique=True)
    is_enabled = BooleanField(default=True)
    password = BlobField(255)

    pw_context = context.CryptContext(
        schemes=['pbkdf2_sha512', 'sha512_crypt'],
        default='pbkdf2_sha512'
    )

    def __repr__(self):
        return "<%s:%s>" % (self.id, self.email)

    class Meta:
        table_name = 'users'

    @staticmethod
    def make_api_key(email, password):
        return make_md5_hash('%s:%s' % (email, password))

    @staticmethod
    def validate_api_key(api_key):
        try:
            # Clients may send api_key in uppercase, lower it
            user = User.get((User.api_key == api_key.lower()) &
                            (User.is_enabled == True))  # noqa
        except User.DoesNotExist:
            return None

        return user

    def check_password(self, input_password):
        passed = User.pw_context.verify(input_password, self.password)
        if not passed:
            return False

        elif User.pw_context.identify(self.password) != User.pw_context.default_scheme():  # noqa
            self.password = User.pw_context.hash(input_password)
            self.save()
            return True
        else:
            return True

    @staticmethod
    def validate_credentials(username_or_email, password):
        '''Lookup for and existing username/e-mail combo and password'''
        try:
            user = User.get(((User.username == username_or_email) |
                            (User.email == username_or_email)) &
                            (User.is_enabled == True))  # noqa
        except User.DoesNotExist:
            return None

        # Do a case-sensitive compare
        if not user.check_password(password):
            return None

        return user

    @staticmethod
    def validate_password(password):
        return len(password) >= User.MIN_PASSWORD_LENGTH

    def hash_password(self, raw=False):
        """
        Set password for user with specified encryption scheme

        For a list of hash schemes see: https://wiki2.dovecot.org/Authentication/PasswordSchemes?action=recall&rev=46
        """
        if raw:
            self.password = self.password
        else:
            self.password = User.pw_context.hash(self.password)


@pre_save(sender=User)
def on_user_save(model, user, created):
    user.api_key = User.make_api_key(user.email, user.password)
    user.hash_password()


class Group(db_wrapper.Model):
    """
    Feed group/folder
    """
    DEFAULT_GROUP = 'Default'

    title = CharField(unique=True)

    class Meta:
        table_name = 'groups'


class Feed(db_wrapper.Model):
    """
    Atom/RSS feed
    """

    DEFAULT_ICON = _ICON
    MAX_TITLE_LENGTH = 255

    is_enabled = BooleanField(default=True)
    self_link = TextField()  # URL of the feed itself (rel=self)
    self_link_hash = CharField(unique=True, max_length=40)
    error_count = IntegerField(default=0)
    title = CharField()
    # URL associated with the feed (rel=alternate)
    alternate_link = TextField(default='')
    etag = CharField(default='')  # HTTP E-tag

    # Nullable fields

    last_updated_on = DateTimeField(null=True)
    last_checked_on = DateTimeField(index=True, null=True)
    last_status = IntegerField(null=True)  # Last returned HTTP code

    icon = TextField(default='')  # Stored as data URI
    icon_last_updated_on = DateTimeField(null=True)

    class Meta:
        table_name = 'feeds'

    @property
    def last_updated_on_as_epoch(self):
        # Never updated?
        if self.last_updated_on:
            return datetime_as_epoch(self.last_updated_on)
        return 0

    @property
    def icon_or_default(self):
        return self.icon if self.icon else Feed.DEFAULT_ICON


@pre_save(sender=Feed)
def on_feed_save(model, feed, created):
    feed.self_link_hash = make_sha1_hash(feed.self_link)


class Entry(db_wrapper.Model):
    """
    Atom/RSS entry
    """

    MAX_TITLE_LENGTH = 255

    guid = TextField()  # 'id' in Atom parlance
    guid_hash = CharField(unique=True, max_length=40)
    feed = ForeignKeyField(Feed, on_delete='CASCADE')
    title = CharField()
    content_type = CharField(default='text/html')
    content = TextField()
    # @@TODO: rename to published_on
    last_updated_on = DateTimeField()
    author = CharField(default='')
    link = TextField(default='')
    # If empty the entry *must* provide a GUID

    class Meta:
        table_name = 'entries'

    @property
    def last_updated_on_as_epoch(self):
        return datetime_as_epoch(self.last_updated_on)


@pre_save(sender=Entry)
def on_entry_save(model, entry, created):
    entry.guid_hash = make_sha1_hash(entry.guid)


class Saved(db_wrapper.Model):
    """
    Entries 'saved' status
    """
    user = ForeignKeyField(User)
    entry = ForeignKeyField(Entry, on_delete='CASCADE')
    saved_on = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = (
            (('user', 'entry'), True),
        )


class Read(db_wrapper.Model):
    """
    Entries 'read' status
    """
    user = ForeignKeyField(User)
    entry = ForeignKeyField(Entry, on_delete='CASCADE')
    read_on = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = (
            (('user', 'entry'), True),
        )


class Subscription(db_wrapper.Model):
    """
    A user's feed subscription
    """
    user = ForeignKeyField(User)
    group = ForeignKeyField(Group, on_delete='CASCADE')
    feed = ForeignKeyField(Feed, on_delete='CASCADE')

    class Meta:
        indexes = (
            (('user', 'group', 'feed'), True),
        )
        table_name = 'subscriptions'


def setup(database):
    """
    Create database and tables for all models and setup bootstrap data
    """
    with database:
        database.create_tables([User, Feed, Entry, Group, Read, Saved,
                                Subscription], safe=True)

    # Create the bare minimum to bootstrap system
    try:
        Group.create(title=Group.DEFAULT_GROUP)
    except IntegrityError:
        return
