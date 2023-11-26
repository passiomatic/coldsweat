"""
Google Reader/FreshRSS API

Specs:
    - https://feedhq.readthedocs.io/en/latest/api/
    - https://github.com/theoldreader/api
    - https://www.inoreader.com/developers/

How to perform an ideal sync between client and server:
    - https://github.com/FreshRSS/FreshRSS/issues/2566#issuecomment-541317776

FreshRSS PHP implementation:
    - https://github.com/FreshRSS/FreshRSS/blob/edge/p/api/greader.php#L280
"""
import struct
from datetime import datetime, timedelta
import time
#from peewee import fn, IntegrityError
import flask
from . import bp
from flask import current_app as app
from ..utilities import datetime_as_epoch
import coldsweat.feed as feed
import coldsweat.models as models
from ..models import (
    User, Feed, Group, Entry, Read, Saved, Subscription)

STREAM_READING_LIST = 'user/-/state/com.google/reading-list'

# Entry states
STREAM_STARRED = 'user/-/state/com.google/starred'
STREAM_READ = 'user/-/state/com.google/read'

STREAM_FEED_PREFIX = 'feed/'
STREAM_LABEL_PREFIX = 'user/-/label/'

ITEM_LONG_FORM_PREFIX = 'tag:google.com,2005:reader/item/'

@bp.route('/accounts/ClientLogin', methods=['GET', 'POST'])
def login():
    email = flask.request.values.get('Email')
    password = flask.request.values.get('Passwd') 

    user = User.validate_credentials(email, password)
    if not user:
        flask.abort(401)

    # @@TODO Use actual session token
    sid, lsid, token = f'{email}/123', f'{email}/123', f'{email}/123'
    payload = f"""SID={sid}\nLSID={lsid}\nAuth={token}\n"""
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
        #"signupTimeSec": 1163850013,
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

    sort_criteria = flask.request.args.get('r', default='n')
    item_count = flask.request.args.get('n', type=int, default=20)
    continuation_string = flask.request.args.get('c', default='')
    excluded_stream_ids = flask.request.args.get('xt')
    included_stream_ids = flask.request.args.get('it')
    min_epoch_timestamp = flask.request.args.get('ot')
    max_epoch_timestamp = flask.request.args.get('nt')

    unread_entries = feed.get_unread_entries(user, Entry)
    payload = {
        "direction": "ltr",
        "author": f"{user.display_name}",
        "title": f"{user.display_name}'s reading list on Coldsweat",
        "updated": 1405538866,
        "continuation": "page2",
        "id": f"user/{user.id}/state/com.google/reading-list",
        "self": [{
            # @@TODO
            "href": "https://feedhq.org/reader/api/0/stream/contents/user/-/state/com.google/reading-list?output=json"
        }],
        "items": []
    }

    return flask.jsonify(payload)

@bp.route('/reader/api/0/stream/items/ids', methods=['GET'])
def get_stream_items_ids():
    user = get_user(flask.request)

    stream_id = flask.request.args.get('s', default=STREAM_READING_LIST)
    item_count = min(flask.request.args.get('n', type=int, default=20), 1000)
    sort_criteria = flask.request.args.get('r', default='n')
    #include_stream_ids = flask.request.args.get('includeAllDirectStreamIds', default=0)
    continuation_string = flask.request.args.get('c', default='')
    excluded_stream_ids = flask.request.args.get('xt')
    included_stream_ids = flask.request.args.get('it')
    min_epoch_timestamp = flask.request.args.get('ot')
    max_epoch_timestamp = flask.request.args.get('nt')

    # Unread 
    # if STREAM_READ in excluded_stream_ids:
    #     q = feed.get_unread_entries(user, Entry.id).objects()
    # elif STREAM_STARRED in included_stream_ids:
    #     q = feed.get_saved_entries(user, Entry.id).objects()
    if stream_id == STREAM_READING_LIST:
        q = feed.get_all_entries(user, Entry.id).objects()        
    elif stream_id == STREAM_READ:
        q = feed.get_read_entries(user, Entry.id).objects()
    elif stream_id == STREAM_STARRED:
        q = feed.get_saved_entries(user, Entry.id).objects()
    elif stream_id.startswith(STREAM_FEED_PREFIX):
        feed_self_link = stream_id[5:]
        q = get_feed_entries(user, feed_self_link).objects()
    elif stream_id.startswith(STREAM_LABEL_PREFIX):
        group_title = stream_id[13:]
        q = get_group_entries(user, group_title).objects()
    else:
        # Bad request
        flask.abort(400)

    if sort_criteria == 'n':
        # Newest entries first
        q = q.order_by(Entry.published_on.desc())
    else:
        # 'd', 'o', or...
        q = q.order_by(Entry.published_on.asc())

    entry_ids = [{'id': to_long_form(r.id)} for r in q.limit(item_count)]
    payload = {
        'itemRefs': entry_ids,
        #'continuation': ''
    }    
    return flask.jsonify(payload)

@bp.route('/reader/api/0/stream/items/contents', methods=['GET', 'POST'])
def get_stream_items_contents():
    user = get_user(flask.request)

    # https://github.com/FreshRSS/FreshRSS/blob/edge/p/api/greader.php#L784
    #item_count = min(flask.request.args.get('n', type=int, default=20), 1000)
    sort_criteria = flask.request.args.get('r', default='n')
    ids = flask.request.values.getlist('i')
    #print(ids)

    if sort_criteria == 'n':
        # Newest entries first
        order_by = Entry.published_on.desc()
    else:
        # 'd', 'o', or...
        order_by = Entry.published_on.asc()

    entries = get_entries(user, ids, order_by)

    items = []
    for entry in entries:
        item = {
            'id': to_long_form(entry.id),
            'crawlTimeMsec': f'{entry.feed.last_updated_on_as_epoch_msec}',            
            'timestampUsec':  f'{entry.feed.last_updated_on_as_epoch_msec * 1000}',  # EasyRSS & Reeder
            'published': entry.published_on_as_epoch,
            'updated': entry.published_on_as_epoch,
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
                'direction': 'ltr',
                'content': entry.content,
            },            
            'categories': [
                # @@TODO Add actual categories
                'user/-/state/com.google/reading-list',
                # @@ Add read/saved info 
            ],
            'origin': {'streamId': f'feed/{entry.feed.self_link}'}
        }
        items.append(item)

    payload = {
        'id': 'user/-/state/com.google/reading-list',
        'updated': time.time(),
        'items': items,
    }
    return flask.jsonify(payload)



@bp.route('/reader/api/0/token', methods=['GET'])
def get_token():
    # @@TODO Make a short-lived token
    return 'token123', 200, {'Content-Type': 'text/plain'}


# @@TODO move to queries.py
def get_feed_entries(user, self_link):
    q =  (Entry.select(Entry.id)
          .join(Feed)
          .join(Subscription) 
          .where(
        (Subscription.user == user) &
        (Feed.self_link == self_link)).distinct())
    return q

def get_group_entries(user, group_title):
    q =  (Entry.select(Entry.id)
          .join(Feed)
          .join(Subscription) 
          .join(Group) 
          .where(
        (Subscription.user == user) &
        (Group.title == group_title)))
    return q

def get_entries(user, ids, sort_criteria):
    q = (Entry.select(Entry, Feed)
         .join(Feed)
         .join(Subscription)
         .where((Subscription.user == user) & (Entry.id << ids))
         .order_by(sort_criteria)
         .distinct())
    return q
    #return _get_entries(user, q)

# def _get_entries(user, q):

#     r = Entry.select(Entry.id).join(Read).where(Read.user == user).objects()
#     s = Entry.select(Entry.id).join(Saved).where(Saved.user == user).objects()

#     read_ids = dict((i.id, None) for i in r)
#     saved_ids = dict((i.id, None) for i in s)

#     result = []
#     for entry in q:
#         result.append({
#             'id': entry.id,
#             'feed_id': entry.feed.id,
#             'title': entry.title,
#             'author': entry.author,
#             'html': entry.content,
#             'url': entry.link,
#             'is_saved': 1 if entry.id in saved_ids else 0,
#             'is_read': 1 if entry.id in read_ids else 0,
#             'created_on_time': entry.published_on_as_epoch
#         })
#     return result

# --------------
# Helpers
# --------------

def to_short_form(long_form):
    """
    Long form
    The prefix `tag:google.com,2005:reader/item/` followed by the ID as an *unsigned* *base 16* number 
      that is *0-padded* so that it's always 16 characters wide.

    Short form
    The ID as a *signed* *base 10* number.

    https://github.com/mihaip/google-reader-api/blob/master/wiki/ItemId.wiki
    """
    value = int(long_form.split('/')[-1], 16)
    return struct.unpack("l", struct.pack("L", value))[0]

def to_long_form(entry_id):
    value = hex(struct.unpack("L", struct.pack("l", entry_id))[0])
    return 'tag:google.com,2005:reader/item/{0}'.format(value[2:].zfill(16))

def get_user(request):
    # Authorization: GoogleLogin auth=<token>
    auth_header = request.headers.get('Authorization', '')
    _, token = auth_header.split("=")
    # @@TODO Check token expiration
    user = User.validate_api_auth_token(token)
    if not user:
        flask.abort(401)
    return user