from pathlib import Path
from datetime import datetime
import pytest
from coldsweat import create_app
from coldsweat.utilities import datetime_as_epoch
from coldsweat.models import User, db_wrapper
from coldsweat import TestingConfig

API_ENDPOINT = "/fever/"
TEST_EMAIL = 'test@example.com'
TEST_DIR = Path(__file__).parent
DEFAULT_PARAMS = {'api': ''}

test_api_key = None

@pytest.fixture()
def app():
    app = create_app(config_class=TestingConfig)
    with open(TEST_DIR.joinpath("test-data.sql"), 'r') as f:
        # https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.executescript
        sql = f.read()
        db_wrapper.database.connection().executescript(sql)

    global test_api_key
    test_user = User.get(User.email == TEST_EMAIL)
    test_api_key = test_user.fever_api_key

    yield app

    db_wrapper.database.connection().close()


@pytest.fixture()
def client(app):
    return app.test_client()

# --------------
# Auth
# --------------


def test_auth_failure(client):
    r = post(client, 'wrong-api-key', query_string=DEFAULT_PARAMS)
    assert r.json['auth'] == 0


def test_endpoint_failure(client):
    r = post(client, 'wrong-api-key')
    assert r.status_code == 400


def test_auth(client):
    r = post(client, test_api_key, query_string=DEFAULT_PARAMS)
    assert r.json['auth'] == 1

# --------------
# Groups
# --------------


def test_groups(client):
    params = DEFAULT_PARAMS | {'groups': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['groups']) > 0

# --------------
# Feeds
# --------------


def test_feeds(client):
    params = DEFAULT_PARAMS | {'feeds': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['feeds']) > 0

# --------------
# Items
# --------------


def test_items_max_id(client):
    params = DEFAULT_PARAMS | {'items': '', 'max_id': '50'}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['items']) > 0


def test_items_since_id(client):
    params = DEFAULT_PARAMS | {'items': '', 'since_id': '50'}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['items']) > 0


def test_items_with_ids(client):
    params = DEFAULT_PARAMS | {'items': '', 'with_ids': '1,2'}
    r = post(client, test_api_key, query_string=params)
    items = r.json['items']
    assert find_id(1, items)
    assert find_id(2, items)


def test_unread_item_ids(client):
    params = DEFAULT_PARAMS | {'unread_item_ids': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['unread_item_ids']) > 0


def test_saved_item_ids(client):
    params = DEFAULT_PARAMS | {'saved_item_ids': ''}
    r = post(client, test_api_key, query_string=params)
    # We don't have any saved items
    assert len(r.json['saved_item_ids']) == 0


def test_mark_item(client):
    form = {'mark': 'item', 'as': 'read', 'id': 1}
    r = post(client, test_api_key, form=form, query_string=DEFAULT_PARAMS)
    assert r.status_code == 200

    params = DEFAULT_PARAMS | {'items': '', 'with_ids': '1'}
    r = post(client, test_api_key, query_string=params)
    items = r.json['items']
    assert len(items) > 0
    read_item = items[0]
    assert read_item['is_read'] == 1


def test_mark_item_not_found(client):
    form = {'mark': 'item', 'as': 'read', 'id': 999}
    r = post(client, test_api_key, form=form, query_string=DEFAULT_PARAMS)
    assert r.status_code == 404


def test_mark_item_malformed(client):
    form = {'mark': 'item', 'as': 'read', 'id': 'wrong'}
    r = post(client, test_api_key, form=form, query_string=DEFAULT_PARAMS)
    assert r.status_code == 400


def test_mark_feed(client):
    before = datetime_as_epoch(datetime.utcnow())
    form = {'mark': 'feed', 'as': 'read', 'id': 1, 'before': before}
    r = post(client, test_api_key, form=form, query_string=DEFAULT_PARAMS)
    assert r.status_code == 200


def test_mark_feed_not_found(client):
    before = datetime_as_epoch(datetime.utcnow())
    form = {'mark': 'feed', 'as': 'read', 'id': 999, 'before': before}
    r = post(client, test_api_key, form=form, query_string=DEFAULT_PARAMS)
    assert r.status_code == 404


def test_mark_feed_malformed(client):
    form = {'mark': 'feed', 'as': 'read', 'id': 1, 'before': 'wrong'}
    r = post(client, test_api_key, form=form, query_string=DEFAULT_PARAMS)
    assert r.status_code == 400


def test_mark_group(client):
    before = datetime_as_epoch(datetime.utcnow())
    form = {'mark': 'group', 'as': 'read', 'id': 1, 'before': before}
    r = post(client, test_api_key, form=form, query_string=DEFAULT_PARAMS)
    assert r.status_code == 200


def test_mark_group_not_found(client):
    before = datetime_as_epoch(datetime.utcnow())
    form = {'mark': 'group', 'as': 'read', 'id': 999, 'before': before}
    r = post(client, test_api_key, form=form, query_string=DEFAULT_PARAMS)
    assert r.status_code == 404


def test_mark_group_malformed(client):
    form = {'mark': 'group', 'as': 'read', 'id': 1, 'before': 'wrong'}
    r = post(client, test_api_key, form=form, query_string=DEFAULT_PARAMS)
    assert r.status_code == 400


def test_undo_read(client):
    params = DEFAULT_PARAMS | { 'unread_recently_read': '1' }
    r = post(client, test_api_key, query_string=params)
    assert r.status_code == 200


# --------------
# Misc.
# --------------

def test_favicons(client):
    params = DEFAULT_PARAMS | {'favicons': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['favicons']) > 0


def test_links(client):
    params = DEFAULT_PARAMS | {'links': ''}
    r = post(client, test_api_key, query_string=params)
    # Unsupported
    assert len(r.json['links']) == 0


def test_multiple_commands(client):
    params = DEFAULT_PARAMS | {'items': '', 'max_id': '50', 'favicons': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['items']) > 0
    assert len(r.json['favicons']) > 0

# --------------
#  Helpers 
# --------------

def find_id(id, items):
    return (id in (item['id'] for item in items))


def post(client, api_key, form=None, query_string=None):
    data={"api_key": api_key}
    if form:
        data.update(form)
    return client.post(API_ENDPOINT, data=data, query_string=(query_string or {}))
