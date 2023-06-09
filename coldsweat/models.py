'''
Database models
'''
from datetime import datetime
from playhouse.signals import (pre_save, Model)
from playhouse.flask_utils import FlaskDB
from playhouse.sqlite_ext import FTS5Model, SearchField, RowIDField
from peewee import (BooleanField, CharField, DateTimeField,
                    ForeignKeyField,
                    IntegerField,
                    TextField)
from werkzeug import security
from .utilities import datetime_as_epoch, make_md5_hash, make_sha1_hash

__all__ = [
    'User',
    'Group',
    'Feed',
    'FeedIndex',
    'Entry',
    'EntryIndex',
    'Read',
    'Saved',
    'Subscription',
    'ColdsweatDB',
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

class ColdsweatDB(FlaskDB):
    '''
    Specialised FlaskDB which deals with testing memory 
      sqlite database, see: https://t.ly/susgy
    '''
    def _register_handlers(self, app):
        if app.config['TESTING']:
            return
        app.before_request(self.connect_db)
        app.teardown_request(self.close_db)


# Pass Peewee Model class with signal support
# See https://docs.peewee-orm.com/en/latest/peewee/playhouse.html#database-wrapper
db_wrapper = ColdsweatDB(model_class=Model)


class User(db_wrapper.Model):
    """
    Coldsweat user
    """

    MIN_PASSWORD_LENGTH = 12

    display_name = CharField(default='')
    email = CharField(unique=True)
    fever_api_key = CharField(unique=True)
    enabled = BooleanField(default=True)
    password = CharField(255)

    def __repr__(self):
        return "<%s:%s>" % (self.id, self.email)

    class Meta:
        table_name = 'users'

    @staticmethod
    def make_fever_api_key(email, password):
        return make_md5_hash('%s:%s' % (email, password))

    @staticmethod
    def validate_fever_api_key(api_key):
        # Clients may send api_key in uppercase, lower it
        return User.get_or_none(User.fever_api_key == api_key.lower(), User.enabled == True)  # noqa

    def check_password(self, input_password):
        return security.check_password_hash(self.password, input_password)

    @staticmethod
    def validate_credentials(email, password):
        user = User.get_or_none(User.email == email, User.enabled == True)  # noqa
        if not user:
            return None

        if not user.check_password(password):
            return None

        return user

    @staticmethod
    def validate_password(password):
        return len(password) >= User.MIN_PASSWORD_LENGTH


@pre_save(sender=User)
def on_user_save(model, user, created):
    user.fever_api_key = User.make_fever_api_key(user.email, user.password)
    user.password = security.generate_password_hash(user.password)


class Group(db_wrapper.Model):
    """
    Feed group/folder
    """
    DEFAULT_GROUP = 'Default'

    title = CharField(unique=True)
    color = CharField(default="#FFFFFF")  # Future use

    class Meta:
        table_name = 'groups'


class Feed(db_wrapper.Model):
    """
    Atom/RSS feed
    """

    DEFAULT_ICON = _ICON
    MAX_TITLE_LENGTH = 255

    enabled = BooleanField(default=True)
    self_link = TextField()  # URL of the feed itself (rel=self)
    self_link_hash = CharField(unique=True, max_length=40)
    error_count = IntegerField(default=0)
    title = CharField(default='')
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
        # Check if never updated
        if self.last_updated_on:
            return datetime_as_epoch(self.last_updated_on)
        return 0

    @property
    def icon_or_default(self):
        return self.icon if self.icon else Feed.DEFAULT_ICON


@pre_save(sender=Feed)
def on_feed_save(model, feed, created):
    feed.self_link_hash = make_sha1_hash(feed.self_link)


class FeedIndex(FTS5Model):
    """
    Full-text search index for feeds
    """
    rowid = RowIDField()
    title = SearchField()

    class Meta:
        database = db_wrapper.database
        options = {'tokenize': 'porter'}


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
    thumbnail_url = CharField(default='')  # Future use
    # @@TODO: rename to published_on
    last_updated_on = DateTimeField()
    author = CharField(default='')
    link = TextField(default='')  # If empty the entry *must* provide a GUID

    class Meta:
        table_name = 'entries'

    @property
    def last_updated_on_as_epoch(self):
        return datetime_as_epoch(self.last_updated_on)


class EntryIndex(FTS5Model):
    """
    Full-text search index for entries
    """
    rowid = RowIDField()
    title = SearchField()
    content = SearchField()
    author = SearchField()

    class Meta:
        database = db_wrapper.database
        options = {'tokenize': 'porter'}


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


BUILTIN_GROUPS = [
    {'id': 1, 'title': Group.DEFAULT_GROUP},
    {'id': 2, 'title': 'Reserved 2'},
    {'id': 3, 'title': "Reserved 3"},
    {'id': 4, 'title': "Reserved 4"},
    {'id': 5, 'title': "Reserved 5"},
    {'id': 6, 'title': "Reserved 6"},
    {'id': 7, 'title': "Reserved 7"},
    {'id': 8, 'title': "Reserved 8"},
    {'id': 9, 'title': "Reserved 9"},
]

def setup():
    """
    Create database and tables for all models and setup bootstrap data
    """
    with db_wrapper.database as database:
        database.create_tables([User, Feed, FeedIndex, Entry, EntryIndex, Group, Read, Saved,
                                Subscription], safe=True)

    # Create the bare minimum to bootstrap system
    (Group.insert_many(BUILTIN_GROUPS)
     .on_conflict(
        conflict_target=[Group.id],
        # Pass down values from insert clause
        preserve=[Group.title]).execute())
