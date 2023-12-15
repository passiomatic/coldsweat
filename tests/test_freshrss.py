from pathlib import Path
from datetime import datetime, timedelta
import pytest
from coldsweat import create_app
from coldsweat.utilities import datetime_as_epoch
from coldsweat.models import User, Entry, Read, Saved, db_wrapper
from coldsweat import TestingConfig

API_ENDPOINT = "/freshrss"
TEST_EMAIL = 'test@example.com'
TEST_PASSWORD = 'secret-password'
TEST_POST_TOKEN = 'token123'
TEST_DIR = Path(__file__).parent


@pytest.fixture()
def app():
    app = create_app(config_class=TestingConfig)
    with open(TEST_DIR.joinpath("test-data.sql"), 'r') as f:
        # https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.executescript
        sql = f.read()
        db_wrapper.database.connection().executescript(sql)

        sample_entries = Entry.select().limit(3)
        test_user = User.get_or_none((User.email==TEST_EMAIL))

        # Mark entry 1 as read and starred
        Read.create(entry=sample_entries[0], user=test_user)
        Saved.create(entry=sample_entries[0], user=test_user)

        # Mark entry 2 as read
        Read.create(entry=sample_entries[1], user=test_user)

        # Mark entry 3 as starred
        Saved.create(entry=sample_entries[2], user=test_user)

    yield app

    db_wrapper.database.connection().close()


@pytest.fixture()
def client(app):
    return app.test_client()

# --------------
# Auth/User
# --------------

AUTH_PATH = '/accounts/ClientLogin'

def test_auth_failure(client):
    auth_args = {
        'Email': 'bob@example.com',
        'Passwd': 'somepassword'
    }
    r = post(client, AUTH_PATH, query_string=auth_args)
    assert r.status_code == 401

def test_auth_failure_2(client):
    auth_args = {
        'Email': '',
        'Passwd': ''
    }
    r = post(client, AUTH_PATH, query_string=auth_args)
    assert r.status_code == 401

def test_auth(client):
    login(client)


def test_user_info(client):
    r = get(client, '/reader/api/0/user-info', query_string={'output': 'json'}, headers=login(client))
    assert r.status_code == 200  
    assert r.json['userEmail'] == TEST_EMAIL


# --------------
# Tag
# --------------

def test_tag_list(client):  
    r = get(client, '/reader/api/0/tag/list', query_string={'output': 'json'}, headers=login(client))
    assert r.status_code == 200    
    assert len(r.json['tags']) > 0
    #print(r.json['tags'])

# --------------
# Feed
# --------------

def test_subscription_list(client):  
    r = get(client, '/reader/api/0/subscription/list', query_string={'output': 'json'}, headers=login(client))
    assert r.status_code == 200    
    assert len(r.json['subscriptions']) > 0
    #print(r.json['subscriptions'])

# --------------
# Stream
# --------------

STREAM_CONTENTS_PATH = '/reader/api/0/stream/contents/'

# def test_stream_contents_reading_list(client): 
#     query_string={
#         'output': 'json',
#         #'r': 'o',
#         'xt': 'user/-/state/com.google/read',
#         'n': 50
#     }
#     r = get(client, STREAM_CONTENTS_PATH + 'user/-/state/com.google/reading-list', query_string=query_string, headers=login(client))
#     assert r.status_code == 200    
#     assert len(r.json['items']) == 50
#     #print(r.json)


# --------------
# Items
# --------------

ITEMS_IDS_PATH = '/reader/api/0/stream/items/ids'
ITEMS_CONTENTS_PATH = '/reader/api/0/stream/items/contents'

def test_items_reading_list(client):  
    query_string={
        'output': 'json',
        's': 'user/-/state/com.google/reading-list',
        'r': 'o',
        'n': 50
    }
    r = get(client, ITEMS_IDS_PATH, query_string=query_string, headers=login(client))
    assert r.status_code == 200    
    assert len(r.json['itemRefs']) == 50
    #print(r.json)

def test_items_starred(client):  
    query_string={
        'output': 'json',
        's': 'user/-/state/com.google/starred',
    }
    r = get(client, ITEMS_IDS_PATH, query_string=query_string, headers=login(client))
    assert r.status_code == 200    
    assert len(r.json['itemRefs']) == 2
    #print(r.json)

def test_items_read(client):  
    # Last month only
    min_datetime = datetime.utcnow() - timedelta(days=30)
    query_string={
        'output': 'json',
        's': 'user/-/state/com.google/read',
        #'ot': int(min_datetime.timestamp())
    }
    r = get(client, ITEMS_IDS_PATH, query_string=query_string, headers=login(client))
    assert r.status_code == 200    
    assert len(r.json['itemRefs']) == 2
    #print(r.json)

def test_items_feed(client):  
    query_string={
        'output': 'json',
        's': 'feed/https://lab.passiomatic.com/coldsweat/tests/feed5.xml',
        'r': 'n',
    }
    r = get(client, ITEMS_IDS_PATH, query_string=query_string, headers=login(client))
    assert r.status_code == 200    
    assert len(r.json['itemRefs']) > 0
    #print(r.json['itemRefs'])

def test_items_label(client):  
    query_string={
        'output': 'json',
        's': 'user/-/label/Graphics',
    }
    r = get(client, ITEMS_IDS_PATH, query_string=query_string, headers=login(client))
    assert r.status_code == 200    
    assert len(r.json['itemRefs']) > 0
    #print(r.json['itemRefs'])

def test_items_contents(client):
    sample_entries = Entry.select().limit(10)

    # Request a few entries 
    entry_ids = [entry.long_form_id for entry in sample_entries]
    query_string={
        'output': 'json',
        'i': entry_ids
    }    
    r = get(client, ITEMS_CONTENTS_PATH, query_string=query_string, headers=login(client))
    assert r.status_code == 200    
    assert len(r.json['items']) == 10
    #print(r.json)

def test_post_token(client):
    r = get(client, '/reader/api/0/token', headers=login(client))    
    assert r.status_code == 200 
    assert r.text == TEST_POST_TOKEN

# --------------
# Edit
# --------------

EDIT_TAG_PATH = '/reader/api/0/edit-tag'
MARK_ALL_READ_PATH = '/reader/api/0/mark-all-as-read'

def test_edit_tag_read(client):
    sample_entries = Entry.select().limit(2)
    entry_ids = [entry.long_form_id for entry in sample_entries]

    request = {        
        'T': TEST_POST_TOKEN,
        'i': entry_ids,
        'a': 'user/-/state/com.google/read' # Mark as read
    }
    r = post(client, EDIT_TAG_PATH, form=request, headers=login(client))
    assert r.status_code == 200
    assert "OK" in r.text

def test_edit_tag_unread(client):
    sample_entries = Entry.select().limit(2)
    entry_ids = [entry.long_form_id for entry in sample_entries]

    request = {        
        'T': TEST_POST_TOKEN,
        'i': entry_ids,
        'r': 'user/-/state/com.google/read' # Mark as unread
    }
    r = post(client, EDIT_TAG_PATH, form=request, headers=login(client))
    assert r.status_code == 200
    assert "OK" in r.text

def test_edit_tag_saved(client):
    sample_entries = Entry.select().limit(2)
    entry_ids = [entry.long_form_id for entry in sample_entries]

    request = {        
        'T': TEST_POST_TOKEN,
        'i': entry_ids,
        'a': 'user/-/state/com.google/starred' # Mark as saved
    }
    r = post(client, EDIT_TAG_PATH, form=request, headers=login(client))
    assert r.status_code == 200
    assert "OK" in r.text

def test_edit_tag_unsaved(client):
    sample_entries = Entry.select().limit(2)
    entry_ids = [entry.long_form_id for entry in sample_entries]

    request = {        
        'T': TEST_POST_TOKEN,
        'i': entry_ids,
        'r': 'user/-/state/com.google/starred' # Mark as unsaved
    }
    r = post(client, EDIT_TAG_PATH, form=request, headers=login(client))
    assert r.status_code == 200
    assert "OK" in r.text

def test_mark_group_read(client):
    request = {        
        'T': TEST_POST_TOKEN,
        's': 'user/-/label/Graphics',
    }
    r = post(client, MARK_ALL_READ_PATH, form=request, headers=login(client))
    assert r.status_code == 200
    assert "OK" in r.text

def test_mark_group_read_404(client):
    request = {        
        'T': TEST_POST_TOKEN,
        's': 'user/-/label/Wrong Label',
    }
    r = post(client, MARK_ALL_READ_PATH, form=request, headers=login(client))
    assert r.status_code == 404

def test_mark_feed_read(client):
    request = {        
        'T': TEST_POST_TOKEN,
        's': 'feed/https://lab.passiomatic.com/coldsweat/tests/feed2.xml',
    }
    r = post(client, MARK_ALL_READ_PATH, form=request, headers=login(client))
    assert r.status_code == 200
    assert "OK" in r.text

def test_mark_feed_read_404(client):
    request = {        
        'T': TEST_POST_TOKEN,
        's': 'feed/https://example.com/not-found.xml',
    }
    r = post(client, MARK_ALL_READ_PATH, form=request, headers=login(client))
    assert r.status_code == 404

# --------------
#  Helpers 
# --------------

def login(client):
    auth_args = {
        'Email': TEST_EMAIL,
        'Passwd': TEST_PASSWORD
    }    
    r = post(client, AUTH_PATH, query_string=auth_args)
    assert "Auth=" in r.text
    _, auth_token = r.text.splitlines()[2].split('=')
    auth_headers = {
        'Authorization': f'GoogleLogin auth={auth_token}'
    }    
    return auth_headers
    

# def find_id(id, items):
#     return (id in (item['id'] for item in items))

def get(client, path, query_string=None, headers={}):
    return client.get(API_ENDPOINT + path, query_string=(query_string or {}), headers=headers)

def post(client, path, form=None, query_string=None, headers={}):
    data = {}
    if form:
        data.update(form)
    return client.post(API_ENDPOINT + path, data=data, query_string=(query_string or {}), headers=headers)
