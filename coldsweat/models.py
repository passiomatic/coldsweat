# -*- coding: utf-8 -*-
"""
Description: database models

Copyright (c) 2013—2016 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
"""
import urllib.parse as urlparse

import pickle

from datetime import datetime

from playhouse.signals import Model, pre_save

from peewee import (BlobField, BooleanField, CharField, DateTimeField,
                    ForeignKeyField,
                    IntegerField, IntegrityError,
                    TextField, SqliteDatabase)
from passlib import context

from coldsweat import config, logger
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
    'connect',
    'close',
    'transaction',
    'setup_database_schema',
    'database'
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

# @@FIXME Use https://docs.peewee-orm.com/en/latest/peewee/database.html#connecting-using-a-database-url


def parse_connection_url(url):
    parsed = urlparse.urlparse(url, scheme='sqlite')
    connect_kwargs = {'database': parsed.path[1:]}
    if parsed.username:
        connect_kwargs['user'] = parsed.username
    if parsed.password:
        connect_kwargs['password'] = parsed.password
    if parsed.hostname:
        connect_kwargs['host'] = parsed.hostname
    if parsed.port:
        connect_kwargs['port'] = parsed.port

    # Adjust parameters for MySQL
    if parsed.scheme == 'mysql' and 'password' in connect_kwargs:
        connect_kwargs['passwd'] = connect_kwargs.pop('password')

    return parsed.scheme, connect_kwargs


engine, kwargs = parse_connection_url(config.database.connection_url)

if engine == 'sqlite':
    database = SqliteDatabase(pragmas={'journal_mode': 'wal',
                                       'foreign_keys': 1},
                              **kwargs)
#
# elif engine == 'mysql':
#    _db = MySQLDatabase(**kwargs)
#    migrator = MySQLMigrator(_db)
# elif engine == 'postgresql':
#    _db = PostgresqlDatabase(autorollback=True, **kwargs)
#    migrator = PostgresqlMigrator(_db)
else:
    raise ValueError(
        'Unknown database engine %s. Should be sqlite, postgresql or mysql'
        % engine)

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


class BaseModel(Model):
    """
    Binds the same database to all models
    """

    class Meta:
        database = database


class User(BaseModel):
    """
    Coldsweat user
    """

    DEFAULT_USERNAME = 'coldsweat'
    MIN_PASSWORD_LENGTH = 8

    username = CharField(unique=True)
    email = CharField(default='')
    api_key = CharField(unique=True)
    is_enabled = BooleanField(default=True)
    password = BlobField(255)

    pw_context = context.CryptContext(
        schemes=['pbkdf2_sha512', 'sha512_crypt'],
        default='pbkdf2_sha512'
    )

    def __repr__(self):
        return "<%s|%s>" % (self.username, self.email)

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


class Group(BaseModel):
    """
    Feed group/folder
    """
    DEFAULT_GROUP = 'Default'

    title = CharField(unique=True)

    class Meta:
        order_by = ('title',)
        table_name = 'groups'


class Feed(BaseModel):
    """
    Atom/RSS feed
    """

    DEFAULT_ICON = _ICON
    MAX_TITLE_LENGTH = 255

    is_enabled = BooleanField(default=True)           # Fetch feed?
    self_link = TextField()   # The URL of the feed itself (rel=self)
    self_link_hash = CharField(unique=True, max_length=40)
    error_count = IntegerField(default=0)

    # Nullable

    title = CharField(null=True)
    alternate_link = TextField(null=True)
    # The URL of the HTML page associated with the feed (rel=alternate)
    etag = CharField(null=True)                 # HTTP E-tag
    last_updated_on = DateTimeField(null=True)             # As UTC
    last_checked_on = DateTimeField(index=True, null=True)  # As UTC
    last_status = IntegerField(null=True)  # Last returned HTTP code

    icon = TextField(null=True)  # Stored as data URI
    icon_last_updated_on = DateTimeField(null=True)  # As UTC

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


class Entry(BaseModel):
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
    last_updated_on = DateTimeField()  # As UTC

    # Nullable

    author = CharField(null=True)
    link = TextField(null=True)
    # If null the entry *must* provide a GUID

    class Meta:
        table_name = 'entries'

    @property
    def last_updated_on_as_epoch(self):
        return datetime_as_epoch(self.last_updated_on)


@pre_save(sender=Entry)
def on_entry_save(model, entry, created):
    entry.guid_hash = make_sha1_hash(entry.guid)


class Saved(BaseModel):
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


class Read(BaseModel):
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


class Subscription(BaseModel):
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


class Session(BaseModel):
    """
    Web session
    """
    key = CharField(unique=True)
    value = PickleField()
    expires_on = DateTimeField()

    class Meta:
        table_name = 'sessions'


# ------------------------------------------------------
# Utility functions
# ------------------------------------------------------

def connect():
    logger.debug('opening connection')
    database.connect(reuse_if_open=True)


def transaction():
    return database.transaction()


def close():
    if not database.is_closed():
        logger.debug('closing connection')
        database.close()


def setup_database_schema():
    """
    Create database and tables for all models and setup bootstrap data
    """
    with database:
        database.create_tables([User, Feed, Entry, Group, Read, Saved,
                                Subscription, Session],
                               safe=True)

    # Create the bare minimum to bootstrap system
    try:
        Group.create(title=Group.DEFAULT_GROUP)
    except IntegrityError:
        return
