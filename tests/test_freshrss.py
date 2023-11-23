from pathlib import Path
from datetime import datetime
import pytest
from coldsweat import create_app
from coldsweat.utilities import datetime_as_epoch
from coldsweat.models import User, db_wrapper
from coldsweat import TestingConfig

API_ENDPOINT = "/freshrss"
TEST_EMAIL = 'test@example.com'
TEST_TOKEN = f'{TEST_EMAIL}/123'
TEST_PASSWORD = 'secret-password'
TEST_DIR = Path(__file__).parent
DEFAULT_PARAMS = {}
AUTH_HEADERS = {
    'Authorization': f'GoogleLogin auth={TEST_TOKEN}'
}

auth_token = None

@pytest.fixture()
def app():
    app = create_app(config_class=TestingConfig)
    with open(TEST_DIR.joinpath("test-data.sql"), 'r') as f:
        # https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.executescript
        sql = f.read()
        db_wrapper.database.connection().executescript(sql)

    yield app

    db_wrapper.database.connection().close()


@pytest.fixture()
def client(app):
    return app.test_client()

# --------------
# Auth
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
    auth_args = {
        'Email': TEST_EMAIL,
        'Passwd': TEST_PASSWORD
    }    
    r = post(client, AUTH_PATH, query_string=auth_args)
    assert b"Auth=" in r.data

# --------------
# Tags
# --------------

def test_tag_list(client):  
    r = get(client, '/reader/api/0/tag/list', query_string={'output': 'json'}, headers=AUTH_HEADERS)
    assert r.status_code == 200    
    assert len(r.json['tags']) > 0
    #print(r.json['tags'])


def test_subscription_list(client):  
    r = get(client, '/reader/api/0/subscription/list', query_string={'output': 'json'}, headers=AUTH_HEADERS)
    assert r.status_code == 200    
    assert len(r.json['subscriptions']) > 0
    #print(r.json['subscriptions'])

# --------------
#  Helpers 
# --------------

def find_id(id, items):
    return (id in (item['id'] for item in items))

def get(client, path, query_string=None, headers={}):
    return client.get(API_ENDPOINT + path, query_string=(query_string or {}), headers=headers)

def post(client, path, form=None, query_string=None, headers={}):
    data = {}
    if form:
        data.update(form)
    return client.post(API_ENDPOINT + path, data=data, query_string=(query_string or {}), headers=headers)
