'''
Database models
'''
from datetime import datetime
from playhouse.signals import (pre_save, Model)
from playhouse.flask_utils import FlaskDB
from peewee import (BooleanField, CharField, FixedCharField, DateTimeField,
                    ForeignKeyField,
                    IntegerField,
                    TextField)
from werkzeug import security
from markupsafe import Markup
from .utilities import datetime_as_epoch, make_md5_hash, make_sha1_hash

__all__ = [
    'User',
    'Group',
    'Feed',
    'Entry',
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

FEED_GENERIC = 'G'
FEED_MASTODON = 'M'
FEED_YOUTUBE = 'Y'
MAX_URL_LENGTH = 3072 // 4  # Stay below the 3072 char limit of recent MySQL versions with 4-byte text encodings

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

    def get_engine(self):
        url = self._app.config["DATABASE_URL"]
        if url.startswith("sqlite") or url.startswith("apsw"):
            return 'sqlite'
        elif url.startswith("mysql"):
            return 'mysql'
        elif url.startswith("postgres"):
            return 'postgres'
        else: 
            raise ValueError(f"Unknown database backend {url}")


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
    fever_api_key = CharField()
    enabled = BooleanField(default=True)
    password_hash = CharField()

    def __repr__(self):
        return "%s:%s" % (self.id, self.email)

    class Meta:
        table_name = 'users'

    @staticmethod
    def make_fever_api_key(email, password):
        return make_md5_hash('%s:%s' % (email, password))

    @staticmethod
    def validate_fever_api_key(api_key):
        # Clients may send api_key in uppercase, lower it
        return User.get_or_none(User.fever_api_key == api_key.lower(), User.enabled == True)  # noqa

    def check_password(self, password):
        return security.check_password_hash(self.password_hash, password)

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
    self_link = CharField(unique=True, max_length=MAX_URL_LENGTH)  # URL of the feed itself (rel=self)
    error_count = IntegerField(default=0)
    title = CharField(default='', max_length=MAX_TITLE_LENGTH)
    # URL associated with the feed (rel=alternate)
    alternate_link = CharField(default='', max_length=MAX_URL_LENGTH)
    etag = CharField(default='')  # HTTP E-tag
    source = FixedCharField(default=FEED_GENERIC, max_length=1)  # Future use

    # Nullable fields

    last_updated_on = DateTimeField(null=True)
    last_checked_on = DateTimeField(index=True, null=True)
    last_status = IntegerField(null=True)  # Last returned HTTP code

    icon = TextField(default='')  # Stored as data URI
    icon_url = CharField(default='', max_length=MAX_URL_LENGTH)
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


class Entry(db_wrapper.Model):
    """
    Atom/RSS entry
    """

    MAX_TITLE_LENGTH = 255

    guid = CharField(unique=True, max_length=MAX_URL_LENGTH)  # 'id' in Atom parlance
    feed = ForeignKeyField(Feed, on_delete='CASCADE')
    title = CharField(max_length=MAX_TITLE_LENGTH)
    content_type = CharField(default='text/html')
    content = TextField()
    thumbnail_url = CharField(default='', max_length=MAX_URL_LENGTH)  # Future use
    published_on = DateTimeField()
    author = CharField(default='')
    link = CharField(default='', max_length=MAX_URL_LENGTH)  # If empty the entry *must* provide a GUID

    class Meta:
        table_name = 'entries'

    @property
    def published_on_as_epoch(self):
        return datetime_as_epoch(self.published_on)

    @property
    def text_content(self):
        '''
        Return entry content suitale for full-text indexing
        '''
        return '\n'.join([self.title, self.author,  Markup(self.content).striptags()])


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
    Create database tables for all models and bootstrap data
    """
    with db_wrapper.database as database:
        database.create_tables([User, Feed, Entry, Group, Read, Saved,
                                Subscription], safe=True)

    Group.insert_many(BUILTIN_GROUPS).on_conflict_replace().execute()
