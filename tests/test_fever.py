from pathlib import Path
from datetime import datetime
import pytest

from coldsweat import create_app
from coldsweat.utilities import datetime_as_epoch
from coldsweat.models import User, db_wrapper
from coldsweat.config import TestingConfig

API_ENDPOINT = "/fever/"
TEST_EMAIL, TEST_PASSWORD = 'test@example.com', 'secret-password'
default_params = {'api': ''}

test_api_key = None

TEST_DIR = Path(__file__).parent


@pytest.fixture()
def app():
    app = create_app(config_class=TestingConfig)
    with open(TEST_DIR.joinpath("test-data.sql"), 'r') as f:
        # https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.executescript
        sql = f.read()
        db_wrapper.database.connection().executescript(sql)

    global test_api_key
    test_api_key = User.make_api_key(TEST_EMAIL, TEST_PASSWORD)

    yield app

    db_wrapper.database.connection().close()


@pytest.fixture()
def client(app):
    return app.test_client()

# --------------
# Auth
# --------------


def test_auth_failure(client):
    r = post(client, 'wrong-api-key', query_string=default_params)
    assert r.json['auth'] == 0


def test_endpoint_failure(client):
    r = post(client, 'wrong-api-key')
    assert r.status_code == 400


def test_auth(client):
    r = post(client, test_api_key, query_string=default_params)
    assert r.json['auth'] == 1

# --------------
# Groups
# --------------


def test_groups(client):
    params = default_params | {'groups': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['groups']) > 0

# --------------
# Feeds
# --------------


def test_feeds(client):
    params = default_params | {'feeds': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['feeds']) > 0

# --------------
# Items
# --------------


def test_items_max_id(client):
    params = default_params | {'items': '', 'max_id': '50'}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['items']) > 0


def test_items_since_id(client):
    params = default_params | {'items': '', 'since_id': '50'}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['items']) > 0


def test_items_with_ids(client):
    params = default_params | {'items': '', 'with_ids': '1,2'}
    r = post(client, test_api_key, query_string=params)
    items = r.json['items']
    assert find_id(1, items)
    assert find_id(2, items)


def test_unread_item_ids(client):
    params = default_params | {'unread_item_ids': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['unread_item_ids']) > 0


def test_saved_item_ids(client):
    params = default_params | {'saved_item_ids': ''}
    r = post(client, test_api_key, query_string=params)
    # We don't have any saved items
    assert len(r.json['saved_item_ids']) == 0


def test_mark_item(client):
    params = default_params | {'mark': 'item', 'as': 'read', 'id': 1}
    r = post(client, test_api_key, query_string=params)
    r.status_code == 200

    params = default_params | {'items': '', 'with_ids': '1'}
    r = post(client, test_api_key, query_string=params)
    items = r.json['items']
    assert len(items) > 0
    read_item = items[0]
    assert read_item['is_read'] == 1


def find_id(id, items):
    return (id in (item['id'] for item in items))


# --------------
# Misc.
# --------------


def test_favicons(client):
    params = default_params | {'favicons': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['favicons']) > 0


def test_links(client):
    params = default_params | {'links': ''}
    r = post(client, test_api_key, query_string=params)
    assert len(r.json['links']) == 0


def post(client, api_key, query_string=None):
    if query_string:
        return client.post(API_ENDPOINT, data={"api_key": api_key},  query_string=query_string)
    else:
        return client.post(API_ENDPOINT, data={"api_key": api_key})


def run_tests(endpoint, suites={}):
    """
    Use curl command line utility to run tests
    """

    epoch = datetime_as_epoch(datetime.utcnow())

    queries = []

    if 'mark_item' in suites:
        queries.extend([
            (True, 'mark=item&as=read&id=1'),
            (True, 'mark=item&as=read&id=1'),                # Dupe
            (True, 'mark=item&as=read&id=0'),                # Does not exist
            (True, 'mark=item&as=unread&id=1'),
            (True, 'mark=item&as=saved&id=1'),
            (True, 'mark=item&as=saved&id=1'),               # Dupe
            (True, 'mark=item&as=saved&id=0'),               # Does not exist
            (True, 'mark=item&as=unsaved&id=1'),
        ])

    if 'mark_feed' in suites:
        queries.extend([
            (True, 'mark=feed&as=read&id=1&before=%d' % epoch),
            (True, 'mark=feed&as=read&id=1&before=abc'),         # Malformed
            (True, 'mark=blah&as=read&id=1&before=%d'
             % epoch),  # Malformed (3)
            (True, 'mark=feed&as=read&id=foo&before=abc'),     # Malformed (4)
            (True, 'mark=feed&as_=read&id=1&before=%d'
             % epoch),    # Malformed (5)
            (True, 'mark=feed&as=read&id=0&before=%d'
             % epoch),  # Does not exist
        ])

    if 'mark_group' in suites:
        queries.extend([
            (True, 'mark=group&as=read&id=1&before=%d' % epoch),
            (True, 'mark=group&as=read&id=1&before=abc'),     # Malformed
            (True, 'mark=group&as=read&id=-1&before=%d'
             % epoch),   # Unsupported
        ])

    if 'mark_all' in suites:
        queries.extend([
            (True, 'mark=group&as=read&id=0&before=%d'
             % epoch),  # Mark all as read
        ])

    if 'unread_read' in suites:
        queries.extend([
            (True, 'unread_recently_read=1')
        ])
