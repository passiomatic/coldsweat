import subprocess

import pytest
from datetime import datetime
import requests

from coldsweat.utilities import datetime_as_epoch
from coldsweat.models import User

API_ENDPOINT = "http://localhost:5000/fever/"
TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD = 'test', 'test@example.com', 'secret'
ALL = ('groups feeds unread_item_ids saved_item_ids favicons items links '
       'unread_recently_read mark_item mark_feed mark_group mark_all').split()
default_params = {'api': ''}

test_user = None
test_api_key = None
def setup_module(module):

    global test_user
    global test_api_key

    test_user = User.get_or_none(User.email == TEST_EMAIL)
    if not test_user:
        test_user = User.create(username=TEST_USERNAME, email=TEST_EMAIL, password=TEST_PASSWORD)
    
    test_api_key = User.make_api_key(TEST_EMAIL, TEST_PASSWORD)


def test_auth_failure():
    r = req('wrong-api-key', params=default_params)
    assert r.json()['auth'] == 0

def test_endpoint_failure():
    r = req('wrong-api-key')
    assert r.status_code == 400

def test_auth():
    r = req(test_api_key, params=default_params)
    assert r.json()['auth'] == 1

def test_groups():
    assert False

def test_feeds():
    assert False

def test_unread_item_ids():
    assert False

def test_saved_item_ids():
    assert False

def test_favicons():
    assert False


def req(api_key, params=None):    
    if params:        
        return requests.post(API_ENDPOINT, data={"api_key": api_key}, params=params)        
    else:
        return requests.post(API_ENDPOINT, data={"api_key": api_key})


def run_tests(endpoint, suites=ALL):
    """
    Use curl command line utility to run tests
    """

    epoch = datetime_as_epoch(datetime.utcnow())

    queries = []

    if 'groups' in suites:
        queries.extend([
            (False, 'groups')
        ])

    if 'feeds' in suites:
        queries.extend([
            (False, 'feeds')
        ])

    if 'unread' in suites:
        queries.extend([
            (False, 'unread_item_ids')
        ])

    if 'saved' in suites:
        queries.extend([
            (False, 'saved_item_ids')
        ])

    if 'favicons' in suites:
        queries.extend([
            (False, 'favicons')
        ])

    if 'items' in suites:
        queries.extend([
            (False, 'items'),
            (False, 'items&with_ids=50,51,52'),
            (False, 'items&max_id=5'),
            (False, 'items&since_id=50')
        ])

    if 'links' in suites:
        queries.extend([
            (False, 'links')                                 # Unsupported
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

