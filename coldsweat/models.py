# -*- coding: utf-8 -*-
"""
Description: database models

Copyright (c) 2013—2015 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
"""

import pickle
from datetime import datetime, timedelta
from peewee import *
from playhouse.migrate import *
from playhouse.signals import Model as BaseModel, pre_save
from playhouse.reflection import Introspector
from webob.exc import status_map

from coldsweat import *
from utilities import *

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
    'migrate_database_schema',
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

class SqliteDatabase_(SqliteDatabase):
    def initialize_connection(self, connection):
        self.execute_sql('PRAGMA foreign_keys=ON;')
        
# Defer database init, see connect() below
engine = config.database.engine
if engine == 'sqlite':
    _db = SqliteDatabase_(None, journal_mode='WAL') 
    migrator = SqliteMigrator(_db)
elif engine == 'mysql':
    _db = MySQLDatabase(None)
    migrator = MySQLMigrator(_db)
elif engine == 'postgresql':
    _db = PostgresqlDatabase(None, autorollback=True)
    migrator = PostgresqlMigrator(_db)
else:
    raise ValueError('Unknown database engine %s. Should be sqlite, postgresql or mysql' % engine)

# ------------------------------------------------------
# Custom fields
# ------------------------------------------------------

class PickleField(BlobField):
    def db_value(self, value):
        return super(PickleField, self).db_value(pickle.dumps(value, 2)) # Use newer protocol 

    def python_value(self, value):
        return pickle.loads(value)

# ------------------------------------------------------
# Coldsweat models
# ------------------------------------------------------

class CustomModel(BaseModel):
    """
    Binds the same database to all models
    """

    class Meta:
        database = _db


class User(CustomModel):
    """
    Coldsweat user
    """    
    DEFAULT_USERNAME = 'coldsweat' 
    MIN_PASSWORD_LENGTH = 8

    username            = CharField(unique=True)
    password            = CharField()  
    email               = CharField(default='')
    api_key             = CharField(unique=True)
    is_enabled          = BooleanField(default=True) 

    class Meta:
        db_table = 'users'
    
    @staticmethod
    def make_api_key(email, password):
        return make_md5_hash(u'%s:%s' % (email, password))

    @staticmethod
    def validate_api_key(api_key):
        try:
            # Clients may send api_key in uppercase, lower it
            user = User.get((User.api_key == api_key.lower()) & 
                (User.is_enabled == True))        
        except User.DoesNotExist:
            return None

        return user

    @staticmethod
    def validate_credentials(username, password):
        try:
            user = User.get((User.username == username) & 
                (User.password == password) & 
                (User.is_enabled == True))        
        except User.DoesNotExist:
            return None

        return user
    
    @staticmethod
    def validate_password(password):
        return len(password) >= User.MIN_PASSWORD_LENGTH
        
@pre_save(sender=User)
def on_user_save(model, user, created):
     user.api_key = User.make_api_key(user.email, user.password)
          

#@@REMOVEME: We keep this only to make migrations work
class Icon(CustomModel):
    """
    Feed (fav)icons, stored as data URIs
    """
    data = TextField() 

    class Meta:
        db_table = 'icons'
      

class Group(CustomModel):
    """
    Feed group/folder
    """
    DEFAULT_GROUP = 'Default'
    
    title = CharField(unique=True)
    
    class Meta:  
        order_by = ('title',)
        db_table = 'groups'    


class Feed(CustomModel):
    """
    Atom/RSS feed
    """

    DEFAULT_ICON         = _ICON
    MAX_TITLE_LENGTH     = 255
    
    is_enabled           = BooleanField(default=True)           # Fetch feed?
    self_link            = TextField()                          # The URL of the feed itself (rel=self)
    self_link_hash       = CharField(unique=True, max_length=40)
    error_count          = IntegerField(default=0)

    # Nullable

    title                = CharField(null=True)        
    alternate_link       = TextField(null=True)                 # The URL of the HTML page associated with the feed (rel=alternate)
    etag                 = CharField(null=True)                 # HTTP E-tag
    last_updated_on      = DateTimeField(null=True)             # As UTC
    last_checked_on      = DateTimeField(index=True, null=True) # As UTC 
    last_status          = IntegerField(null=True)              # Last returned HTTP code    

    icon                 = TextField(null=True)                 # Stored as data URI
    icon_last_updated_on = DateTimeField(null=True)             # As UTC

    class Meta:
        db_table = 'feeds'

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
      
        
class Entry(CustomModel):
    """
    Atom/RSS entry
    """

    MAX_TITLE_LENGTH    = 255

    guid                = TextField()                           # 'id' in Atom parlance
    guid_hash           = CharField(unique=True, max_length=40)   
    feed                = ForeignKeyField(Feed, on_delete='CASCADE')
    title               = CharField()    
    content_type        = CharField(default='text/html')
    content             = TextField()
    #@@TODO: rename to published_on
    last_updated_on     = DateTimeField()                       # As UTC

    # Nullable

    author              = CharField(null=True)
    link                = TextField(null=True)                  # If null the entry *must* provide a GUID
    
    class Meta:
        db_table = 'entries'

    @property
    def last_updated_on_as_epoch(self):
        return datetime_as_epoch(self.last_updated_on)

@pre_save(sender=Entry)
def on_entry_save(model, entry, created):
    entry.guid_hash = make_sha1_hash(entry.guid)    

                
class Saved(CustomModel):
    """
    Entries 'saved' status 
    """
    user            = ForeignKeyField(User)
    entry           = ForeignKeyField(Entry, on_delete='CASCADE')    
    saved_on        = DateTimeField(default=datetime.utcnow)  

    class Meta:
        indexes = (
            (('user', 'entry'), True),
        )


class Read(CustomModel):
    """
    Entries 'read' status 
    """
    user           = ForeignKeyField(User)
    entry          = ForeignKeyField(Entry, on_delete='CASCADE')    
    read_on        = DateTimeField(default=datetime.utcnow) 

    class Meta:
        indexes = (
            (('user', 'entry'), True),
        )


class Subscription(CustomModel):
    """
    A user's feed subscription
    """
    user           = ForeignKeyField(User)
    group          = ForeignKeyField(Group, on_delete='CASCADE')
    feed           = ForeignKeyField(Feed, on_delete='CASCADE')

    class Meta:
        indexes = (
            (('user', 'group', 'feed'), True),
        )    
        db_table = 'subscriptions'


class Session(CustomModel):
    """
    Web session
    """    
    key             = CharField(unique=True)
    value           = PickleField()     
    expires_on      = DateTimeField()

    class Meta:
        db_table = 'sessions' 


# ------------------------------------------------------
# Utility functions
# ------------------------------------------------------

def _init_sqlite():
    _db.init(config.database.database)    

def _init_mysql():
    kwargs = dict(
        host        = config.database.hostname,
        user        = config.database.username,
        password    = config.database.password        
    )
    _db.init(config.database.database, **kwargs)

_init_postgresql = _init_mysql # Alias

ENGINES = {
    'sqlite'    : _init_sqlite,
    'mysql'     : _init_mysql,
    'postgresql': _init_postgresql,        
}

def connect():
    """
    Shortcut to init and connect to database
    """
    ENGINES[engine]()
    _db.connect()

def transaction():
    return _db.transaction()

def close():
    if not _db.is_closed():
        _db.close()

def migrate_database_schema():
    '''
    Migrate database schema from previous versions (0.9.4 and up)
    '''

    introspector = Introspector.from_database(_db)
    models = introspector.generate_models()
    Feed_ = models['feeds']
    Entry_ = models['entries']

    drop_table_migrations, column_migrations = [], []
    
    # --------------------------------------------------------------------------
    # Schema changes introduced in version 0.9.4
    # --------------------------------------------------------------------------
    
    # Change columns

    if hasattr(Feed_, 'icon_id'):
        column_migrations.append(migrator.drop_column('feeds', 'icon_id'))

    if not hasattr(Feed_, 'icon'):
        column_migrations.append(migrator.add_column('feeds', 'icon', Feed.icon))

    if not hasattr(Feed_, 'icon_last_updated_on'):
        column_migrations.append(migrator.add_column('feeds', 'icon_last_updated_on', Feed.icon_last_updated_on))
        
    if not hasattr(Entry_, 'content_type'):
        column_migrations.append(migrator.add_column('entries', 'content_type', Entry.content_type))

    # Drop tables

    if Icon.table_exists():
        drop_table_migrations.append(Icon.drop_table)

    # --------------------------------------------------------------------------
    # Schema changes introduced in version 0.9.5
    # --------------------------------------------------------------------------
    
    # Change columns

    class UpdateFeedSelfLinkHashOperation(object):
        # Fake migrate.Operation protocol and upon saving populate all self_link_hash fields
        def run(self):        
            for feed in Feed.select():
                feed.save()

    class UpdateEntryGuidHashOperation(object):
        def run(self):        
            for entry in Entry.select():
                entry.save()

    class UpdateUserApiKeyOperation(object):
        def run(self):        
            for user in User.select():
                user.save()
                
    if not hasattr(Feed_, 'self_link_hash'):
        # Start relaxing index constrains to cope with existing data...
        self_link_hash = CharField(null=True, max_length=40)
        column_migrations.append(migrator.add_column('feeds', 'self_link_hash', self_link_hash))
        column_migrations.append(UpdateFeedSelfLinkHashOperation())
        # ...and make them strict again
        column_migrations.append(migrator.add_index('feeds', ('self_link_hash',), True))
        
    if not hasattr(Entry_, 'guid_hash'):
        # Start relaxing index constrains to cope with existing data...    
        guid_hash = CharField(null=True, max_length=40)
        column_migrations.append(migrator.add_column('entries', 'guid_hash', guid_hash))
        column_migrations.append(UpdateEntryGuidHashOperation())
        # ...and make them strict again
        column_migrations.append(migrator.add_index('entries', ('guid_hash',), True))

    # Drop obsolete indices
    
    if Feed_.self_link.unique:
        column_migrations.append(migrator.drop_index('feeds', 'feeds_self_link'))
    
    if Entry_.link.index:
        column_migrations.append(migrator.drop_index('entries', 'entries_link'))

    if Entry_.guid.index:
        column_migrations.append(migrator.drop_index('entries', 'entries_guid'))        

    # Misc.
        
    column_migrations.append(UpdateUserApiKeyOperation())
        
    # --------------------------------------------------------------------------
    
    # Run all table and column migrations

    if column_migrations:
        # Let caller to catch any OperationalError's
        migrate(*column_migrations)        

    for drop in drop_table_migrations:
        drop()

    # True if at least one is non-empty
    return drop_table_migrations or column_migrations


def setup_database_schema():
    """
    Create database and tables for all models and setup bootstrap data
    """

    models = User, Feed, Entry, Group, Read, Saved, Subscription, Session

    for model in models:
        model.create_table(fail_silently=True)

    # Create the bare minimum to boostrap system
    with transaction():
        
        # Avoid duplicated default group
        try:
            Group.create(title=Group.DEFAULT_GROUP)        
        except IntegrityError:
            return
