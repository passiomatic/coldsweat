import subprocess

import pytest
from datetime import datetime

from coldsweat.utilities import datetime_as_epoch
from coldsweat.models import User
from coldsweat.app import create_app

API_ENDPOINT = "/fever/"
TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD = 'test', 'test@example.com', 'secret'
ALL = ('groups feeds unread_item_ids saved_item_ids favicons items links '
       'unread_recently_read mark_item mark_feed mark_group mark_all').split()
default_params = {'api': ''}

test_user = None
test_api_key = None


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    # Make sure we have a test user in database
    
    global test_user
    global test_api_key

    test_user = User.get_or_none(User.email == TEST_EMAIL)
    if not test_user:
        test_user = User.create(username=TEST_USERNAME,
                                email=TEST_EMAIL, password=TEST_PASSWORD)

    test_api_key = User.make_api_key(TEST_EMAIL, TEST_PASSWORD)

    yield app


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


def test_unread_with_ids(client):
    params = default_params | {'items': '', 'with_ids': '50,51,52'}
    r = post(client, test_api_key, query_string=params)
    items = r.json['items']
    assert find_id(50, items)
    assert find_id(51, items)
    assert find_id(52, items)


def find_id(id, items):
    return (id in (item['id'] for item in items))


def test_saved_item_ids(client):
    assert False

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


def run_tests(endpoint, suites=ALL):
    """
    Use curl command line utility to run tests
    """

    epoch = datetime_as_epoch(datetime.utcnow())

    queries = []

    if 'unread' in suites:
        queries.extend([
            (False, 'unread_item_ids')
        ])

    if 'saved' in suites:
        queries.extend([
            (False, 'saved_item_ids')
        ])

    if 'items' in suites:
        queries.extend([
            (False, 'items'),
            (False, 'items&with_ids=50,51,52'),
            (False, 'items&max_id=5'),
            (False, 'items&since_id=50')
        ])

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
