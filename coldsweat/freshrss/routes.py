"""
A partial Google Reader-like API implementation

Specs:
    - https://feedhq.readthedocs.io/en/latest/api/
    - https://github.com/theoldreader/api
    - https://www.inoreader.com/developers/
    - https://web.archive.org/web/20090820230934/http://blog.martindoms.com/2009/08/15/using-the-google-reader-api-part-1/
    - https://web.archive.org/web/20091103085510/http://blog.martindoms.com/2009/10/16/using-the-google-reader-api-part-2/

How to perform an ideal sync between client and server:
    - https://github.com/FreshRSS/FreshRSS/issues/2566#issuecomment-541317776

FreshRSS PHP implementation:
    - https://github.com/FreshRSS/FreshRSS/blob/edge/p/api/greader.php
"""
import struct
import operator
from functools import reduce
from datetime import datetime, timezone
from peewee import JOIN, IntegrityError
import flask
from . import bp
from flask import current_app as app
import coldsweat.feed as feed
import coldsweat.models as models
from ..models import (
    User, Feed, Group, Entry, Read, Saved, Subscription)

# Entry states
STREAM_READING_LIST = 'user/-/state/com.google/reading-list'
STREAM_STARRED = 'user/-/state/com.google/starred'
STREAM_READ = 'user/-/state/com.google/read'
STREAM_UNREAD = 'user/-/state/com.google/kept-unread'

STREAM_FEED_PREFIX = 'feed/'
STREAM_LABEL_PREFIX = 'user/-/label/'

ITEM_LONG_FORM_PREFIX = 'tag:google.com,2005:reader/item/'

MAX_ITEMS_IDS = 1000

@bp.route('/accounts/ClientLogin', methods=['GET', 'POST'])
def client_login():
    email = flask.request.values.get('Email', default='')
    password = flask.request.values.get('Passwd', default='') 

    user = User.validate_credentials(email, password)
    if not user:
        flask.abort(401)

    utc_now = datetime.utcnow()
    # Check if never generated or expired
    if (not user.api_auth_token_expires_on) or (utc_now > user.api_auth_token_expires_on):
        new_auth_token_expiration, new_auth_token = User.make_api_auth_token(user.email, app.config.get("SECRET_KEY"))
        user.api_auth_token = new_auth_token
        user.auth_token_expiration = new_auth_token_expiration
        user.save()
        
    payload = f"SID=null\nLSID=null\nAuth={user.api_auth_token}\n"
    return payload, 200, {'Content-Type': 'text/plain'}

@bp.route('/reader/api/0/user-info', methods=['GET'])
def get_user_info():
    user = get_user(flask.request)

    payload = {
        "userId": f"{user.id}",
        "userName": user.display_name,
        "userProfileId": f"{user.id}",
        "userEmail": user.email,
        "isBloggerUser": False,
        "isMultiLoginEnabled": False,
    }
    return flask.jsonify(payload)

@bp.route('/reader/api/0/tag/list', methods=['GET'])
def get_tag_list():
    user = get_user(flask.request)

    tag_list = [{
        'id': f'user/{user.id}/state/com.google/starred',
        'sortid': 'A00000000'
    }
    ]

    groups = feed.get_groups(user)
    tag_list.extend([{
        'id':  f'user/{user.id}/label/{group.title}',
        'sortid': f'A{group.id:08}',
    } for group in groups])

    payload = {
        'tags': tag_list
    }
    return flask.jsonify(payload)


@bp.route('/reader/api/0/subscription/list', methods=['GET'])
def get_subscription_list():
    user = get_user(flask.request)
    groups = feed.get_groups(user)

    subscription_list = []
    for group in groups:
        feeds = feed.get_group_feeds(user, group)
        for feed_ in feeds: 
            subscription_list.append({
                'id': f'feed/{feed_.self_link}',
                'title': feed_.title,
                'url': feed_.self_link,
                'htmlUrl': feed_.alternate_link,
                'iconUrl': feed_.icon_url,
                #'sortid': f'A{feed.id:08}',
                # @@TODO
                # https://stackoverflow.com/a/4429974
                #'firstitemmsec': 0,
                'categories': [            
                    {
                        'id': f'user/-/label/{group.title}',
                        'label': group.title,
                    },            
                ]
            })

    payload = {
        'subscriptions': subscription_list
    }
    return flask.jsonify(payload)


@bp.route('/reader/api/0/stream/contents/<stream_id>', methods=['GET'])
def get_stream_contents(stream_id):
    user = get_user(flask.request)

    rank = flask.request.args.get('r', default='n')
    entry_count = min(flask.request.args.get('n', type=int, default=100), MAX_ITEMS_IDS)
    offset = flask.request.args.get('c', type=int, default=0)
    #include_direct_stream_ids = flask.request.args.get('includeAllDirectStreamIds', default=0)
    included_stream_ids = flask.request.args.getlist('it')
    excluded_stream_ids = flask.request.args.getlist('xt')
    min_timestamp = flask.request.args.get('ot')
    max_timestamp = flask.request.args.get('nt')

    if rank == 'n':
        # Newest entries first
        sort_order = Entry.published_on.desc()
    else:
        # 'd', 'o', or...
        sort_order = Entry.published_on.asc()

    q = (get_filtered_entries(
        user, 
        sort_order, 
        stream_id, 
        included_stream_ids, 
        excluded_stream_ids, 
        min_timestamp)
        .offset(offset).limit(entry_count))

    reader_entries = [make_google_reader_item(entry) for entry in q]  
    payload = {
        "direction": "ltr",
        "id": f"user/{user.id}/state/com.google/reading-list",
        "title": f"{user.display_name}'s reading list on Coldsweat",
        "author": f"{user.display_name}",
        "updated": int(datetime.utcnow().timestamp()),
        # @@TODO 
        # "self":[{"href":"http://www.google.com/reader/api/0/stream/contents/feed/http://astronomycast.com/podcast.xml?"}],
        # "alternate":[{"href":"http://www.astronomycast.com","type":"text/html"}],            
        "self": [{
            "href": ""
        }],
        "items": reader_entries
    }

    # Check if we have finished
    if entry_count == len(reader_entries):
        payload['continuation'] = f'{offset + MAX_ITEMS_IDS}'

    return flask.jsonify(payload)


@bp.route('/reader/api/0/stream/items/ids', methods=['GET'])
def get_stream_items_ids():
    user = get_user(flask.request)

    stream_id = flask.request.args.get('s', default=STREAM_READING_LIST)
    rank = flask.request.args.get('r', default='n')
    entry_count = min(flask.request.args.get('n', type=int, default=100), MAX_ITEMS_IDS)
    offset = flask.request.args.get('c', type=int, default=0)
    #include_direct_stream_ids = flask.request.args.get('includeAllDirectStreamIds', default=0)
    included_stream_ids = flask.request.args.getlist('it')
    excluded_stream_ids = flask.request.args.getlist('xt')
    min_timestamp = flask.request.args.get('ot')
    max_timestamp = flask.request.args.get('nt')

    if rank == 'n':
        # Newest entries first
        sort_order = Entry.published_on.desc()
    else:
        # 'd', 'o', or...
        sort_order = Entry.published_on.asc()

    q = (get_filtered_entries(
        user, 
        sort_order, 
        stream_id, 
        included_stream_ids, 
        excluded_stream_ids, 
        min_timestamp)
        .offset(offset).limit(entry_count))

    entry_ids = [{'id': f'{e.id}'} for e in q]
    payload = {
        'itemRefs': entry_ids,
    }    

    # Check if we have finished
    if entry_count == len(entry_ids):
        payload['continuation'] = f'{offset + MAX_ITEMS_IDS}'

    return flask.jsonify(payload)


@bp.route('/reader/api/0/stream/items/contents', methods=['GET', 'POST'])
def get_stream_items_contents():
    user = get_user(flask.request)

    # https://github.com/FreshRSS/FreshRSS/blob/edge/p/api/greader.php#L784
    rank = flask.request.values.get('r', default='n')
    ids = flask.request.values.getlist('i', type=to_short_form)

    if rank == 'n':
        # Newest entries first
        sort_order = Entry.published_on.desc()
    else:
        # 'd', 'o', or...
        sort_order = Entry.published_on.asc()

    q = get_entries_with_ids(user, ids, sort_order)
    reader_entries = [make_google_reader_item(entry) for entry in q]    
    payload = {
        'id': 'user/-/state/com.google/reading-list',
        'updated': int(datetime.utcnow().timestamp()),
        'items': reader_entries,
    }
    return flask.jsonify(payload)


def make_google_reader_item(entry):
    item = {
        'id': f'{entry.id}',
        'crawlTimeMsec': f'{entry.feed.last_updated_on_as_epoch_msec}',            
        'timestampUsec': f'{entry.published_on_as_epoch_msec * 1000}',  # EasyRSS & Reeder
        'published': entry.published_on_as_epoch,
        #'updated': entry.published_on_as_epoch,
        'title': entry.title,
        'author': entry.author,
        'canonical': [
            {'href': entry.link}
        ],
        'alternate': [
            {
                'href': entry.link,
                'type': entry.content_type,
            },                    
        ],
        'content': {
            #'direction': 'ltr',
            'content': entry.content,
        },            
        'categories': [
            # @@TODO Add actual categories
            'user/-/state/com.google/reading-list',
        ],
        'origin': {
            'streamId': f'feed/{entry.feed.self_link}',
            'htmlUrl': entry.feed.alternate_link,
            'title': entry.feed.title,
            'feedUrl': entry.feed.self_link
        }
    }    
    # Add states
    if entry.read_on:
        item['categories'].append(STREAM_READ)
    else:
        item['categories'].append(STREAM_UNREAD)

    if entry.saved_on:
        item['categories'].append(STREAM_STARRED)    

    return item


# --------------
# Edit
# --------------

@bp.route('/reader/api/0/token', methods=['GET'])
def get_token():
    # @@TODO Make a short-lived token
    return 'token123', 200, {'Content-Type': 'text/plain'}


@bp.route('/reader/api/0/edit-tag', methods=['POST'])
def post_edit_tag():
    user = get_user(flask.request)

    # @@TODO
    #validate_post_token(user, flask.request)
    ids = flask.request.form.getlist('i', type=to_short_form)
    add_tags = flask.request.form.getlist('a')
    remove_tags = flask.request.form.getlist('r')

    for entry in Entry.select().where((Entry.id << ids)):
        # Mark as read 
        if (STREAM_READ in add_tags) or (STREAM_UNREAD in remove_tags):
            try:
                Read.create(user=user, entry=entry)
            except IntegrityError:
                app.logger.debug(f'entry {entry.id} already marked as read, ignored')

        # Mark as unread
        if (STREAM_UNREAD in add_tags) or (STREAM_READ in remove_tags):
            count = Read.delete().where(
                (Read.user == user) & (Read.entry == entry)).execute()
            if not count:
                app.logger.debug(f'entry {entry.id} never marked as read, ignored')

        # Mark as saved 
        if STREAM_STARRED in add_tags:
            try:
                Saved.create(user=user, entry=entry)
            except IntegrityError:
                app.logger.debug(f'entry {entry.id} already marked as saved, ignored')            

        # Mark as unsaved 
        if STREAM_STARRED in remove_tags:
            count = Saved.delete().where(
                (Saved.user == user) & (Saved.entry == entry)).execute()
            if not count:
                app.logger.debug(f'entry {entry.id} never marked as saved, ignored')

    return 'OK', 200, {'Content-Type': 'text/plain'}


@bp.route('/reader/api/0/mark-all-as-read', methods=['POST'])
def post_mark_all_read():
    user = get_user(flask.request)
    stream_id = flask.request.form.get('s')
    max_timestamp = flask.request.form.get('ts', type=int, default=0) # As microseconds

    # @@TODO    
    #validate_post_token(user, flask.request)
    
    if max_timestamp:
        try:
            # Convert in seconds
            max_datetime = datetime.fromtimestamp(max_timestamp / (10**6), timezone.utc)
        except ValueError as ex:
            app.logger.debug(
                f'invalid ts parameter ({ex})')
            flask.abort(400)
    else:
        max_datetime = datetime.utcnow()

    # Feed
    if stream_id.startswith(STREAM_FEED_PREFIX):
        # feed/<feed url>
        self_link = stream_id.replace(STREAM_FEED_PREFIX, '', 1)
        try:
            # @@TODO Check if user is subscribed to this feed 
            feed = Feed.get(Feed.self_link == self_link)
        except Feed.DoesNotExist:
            app.logger.warning(f'could not find feed {self_link}')
            flask.abort(404)        

        q = (Entry.select()
             .join(Feed)
             .join(Subscription)
             .where((Subscription.user == user) & (Subscription.feed == feed) &
                    # Exclude entries already marked as read
                    ~(Entry.id << Read.select(Read.entry).where(
                        Read.user == user)) &
                    # Exclude entries fetched after last sync
                    (Entry.published_on < max_datetime)
                    ).distinct())

    # Label 
    elif stream_id.startswith(STREAM_LABEL_PREFIX):
        # user/-/label/<name> 
        group_title = stream_id.replace(STREAM_LABEL_PREFIX, '', 1)

        try:
            # @@TODO Check if user is subscribed to this gourp 
            group = Group.get(Group.title == group_title)
        except Group.DoesNotExist:
            app.logger.warning(f'could not find group {group_title}')
            flask.abort(404)

        q = (Entry.select()
             .join(Feed)
             .join(Subscription)
             .where((Subscription.user == user) & (Subscription.group == group) &
                    # Exclude entries already marked as read
                    ~(Entry.id << Read.select(
                        Read.entry).where(Read.user == user)) &
                    # Exclude entries fetched after last sync
                    (Entry.published_on < max_datetime)
                    ).distinct())
    
    elif stream_id == STREAM_READING_LIST:
        # @@TODO
        raise NotImplementedError()

    with models.db_wrapper.database.transaction():
        for entry in q:
            try:
                Read.create(user=user, entry=entry)
            except IntegrityError:
                # Should not happen thanks to the query above
                app.logger.warning(f'entry {entry.id} already marked as read, ignored')
                continue

    return 'OK', 200, {'Content-Type': 'text/plain'}


# --------------
# Helpers
# --------------

def get_filtered_entries(user, sort_order, stream, include_streams, exclude_streams, min_timestamp):

    # Always filter on current user 
    where_clauses = [
        (Subscription.user == user)
    ]

    # Read
    if stream == STREAM_READ or (STREAM_READ in include_streams):
        where_clauses.append(
            (Entry.id << Read.select(Read.entry).where(Read.user == user))
        )        

    # Unread/exclude read
    if stream == STREAM_UNREAD or (STREAM_READ in exclude_streams):
        where_clauses.append(
            ~(Entry.id << Read.select(Read.entry).where(Read.user == user))
        )  

    # Saved
    if (stream == STREAM_STARRED) or (STREAM_STARRED in include_streams):
        where_clauses.append(
            (Entry.id << Saved.select(Saved.entry).where(Saved.user == user))   
        )        

    # Feed
    if stream.startswith(STREAM_FEED_PREFIX):
        feed_self_link = stream.replace(STREAM_FEED_PREFIX, '', 1)
        where_clauses.append(
            (Feed.self_link == feed_self_link)    
        )

    # Group
    if stream.startswith(STREAM_LABEL_PREFIX):
        group_title = stream.replace(STREAM_LABEL_PREFIX, '', 1)
        where_clauses.append(
            (Group.title == group_title)  
        )

    if min_timestamp:
        min_datetime = datetime.fromtimestamp(float(min_timestamp), tz=timezone.utc)
        where_clauses.append(
            (Entry.published_on >= min_datetime)
        )

    # Start with returning the 'reading list' (all entries) and apply any given filter
    q = (Entry.select(Entry, Feed, Read.read_on.alias("read_on"), Saved.saved_on.alias("saved_on"))
         .join(Feed)
         .join(Subscription)
         .join(Group)          
         .switch(Entry)
         .join(Read, JOIN.LEFT_OUTER)
         .switch(Entry)         
         .join(Saved, JOIN.LEFT_OUTER)
         # Chain all conditions together AND'ing them 
         #  https://github.com/coleifer/peewee/issues/391#issuecomment-468042229
         .where(reduce(operator.and_, where_clauses))
         .order_by(sort_order)
         .distinct()
         .objects())
    return q

def get_entries_with_ids(user, ids, sort_order):
    q = (Entry.select(Entry, Feed, Read.read_on.alias("read_on"), Saved.saved_on.alias("saved_on"))
         .join(Feed)
         .join(Subscription)
         .switch(Entry)
         .join(Read, JOIN.LEFT_OUTER)
         .switch(Entry)         
         .join(Saved, JOIN.LEFT_OUTER)
         .where((Subscription.user == user) & (Entry.id << ids))
         .order_by(sort_order)
         .distinct()
         .objects())
    return q



def to_short_form(long_form):
    """
    Long form
    The prefix `tag:google.com,2005:reader/item/` followed by the ID as an *unsigned* *base 16* number 
      that is *0-padded* so that it's always 16 characters wide.

    Short form
    The ID as a *signed* *base 10* number.

    https://github.com/mihaip/google-reader-api/blob/master/wiki/ItemId.wiki
    """
    # Check if short form already
    if long_form.isnumeric():
        return int(long_form)

    # Handle long_form values with or without tag:... prefix
    value = int(long_form.split('/')[-1], 16)
    return struct.unpack("l", struct.pack("L", value))[0]


def get_user(request):
    # Authorization: GoogleLogin auth=<token>
    auth_header = request.headers.get('Authorization', '')
    _, token = auth_header.split("=")
    user = User.validate_api_auth_token(token)
    if not user:
        flask.abort(401)
    return user

# https://github.com/FreshRSS/FreshRSS/blob/edge/p/api/greader.php#L246
# def validate_post_token(user, request):
#     token = request.values.get('T', default='')
#     # @@TODO Check token expiration
#     user = User.validate_api_post_token(token)
#     if not user:
#         flask.abort(401)
#     return user