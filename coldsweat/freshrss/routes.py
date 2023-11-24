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
import re
import struct
from datetime import datetime, timedelta
from peewee import fn, IntegrityError
import flask
from . import bp
from flask import current_app as app
from ..utilities import datetime_as_epoch
import coldsweat.feed as feed
import coldsweat.models as models
from ..models import (
    User, Feed, Group, Entry, Read, Saved, Subscription)

# All entries
STREAM_READING_LIST = 'user/-/state/com.google/reading-list'
# Starred entries
STREAM_STARRED = 'user/-/state/com.google/starred'
STREAM_READ = 'user/-/state/com.google/read'

@bp.route('/accounts/ClientLogin', methods=['GET', 'POST'])
def login():
    email = flask.request.values.get('Email')
    password = flask.request.values.get('Passwd') 

    user = User.validate_credentials(email, password)
    if not user:
        flask.abort(401)

    # @@TODO Use actual session token
    sid, lsid, token = f'{email}/123', f'{email}/123', f'{email}/123'
    payload = f"""
SID={sid}\n
LSID={lsid}\n
Auth={token}\n
    """
    return (payload, 200)

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

    sort_criteria = flask.request.args.get('r')
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
            "href": "https://feedhq.org/reader/api/0/stream/contents/user/-/state/com.google/reading-list?output=json"
        }],
        "items": []
    }

    return flask.jsonify(payload)

@bp.route('/reader/api/0/stream/items/ids', methods=['GET'])
def get_stream_ids():
    user = get_user(flask.request)

    stream_id = flask.request.args.get('s')
    item_count = min(flask.request.args.get('n', type=int, default=100), 1000)
    #include_stream_ids = flask.request.args.get('includeAllDirectStreamIds', default=0)
    continuation_string = flask.request.args.get('c', default='')
    excluded_stream_ids = flask.request.args.get('xt')
    included_stream_ids = flask.request.args.get('it')
    min_epoch_timestamp = flask.request.args.get('ot')
    max_epoch_timestamp = flask.request.args.get('nt')

    # Unread 
    if STREAM_READ in excluded_stream_ids:
        q = feed.get_unread_entries(user, Entry.id).objects()
    elif STREAM_STARRED in included_stream_ids:
        q = feed.get_saved_entries(user, Entry.id).objects()

    entry_ids = [{'id': r.id} for r in q]
    payload = {
        'itemRefs': entry_ids
    }    
    return flask.jsonify(payload)

# --------------
# Helpers
# --------------

# def to_long_form(short_form):
#     value = hex(struct.unpack("L", struct.pack("l", short_form))[0])
#     if value.endswith("L"):
#         value = value[:-1]
#     return 'tag:google.com,2005:reader/item/{0}'.format(
#         value[2:].zfill(16)
#     )

# def to_short_form(long_form):
#     value = int(long_form.split('/')[-1], 16)
#     return struct.unpack("l", struct.pack("L", value))[0]

def get_user(request):
    # Authorization: GoogleLogin auth=<token>
    auth_header = request.headers.get('Authorization', '')
    _, token = auth_header.split("=")
    # @@TODO Check token expiration
    user = User.validate_api_auth_token(token)
    if not user:
        flask.abort(401)
    return user