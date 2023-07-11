'''
Feed fetcher tests
'''
from pathlib import Path
from requests.exceptions import RequestException
import pytest
from coldsweat import create_app
from coldsweat.models import db_wrapper
from coldsweat import TestingConfig

from coldsweat import fetcher

TEST_DIR = Path(__file__).parent
TEST_FEEDS = (
    ('http://www.aaa.bbb/', None),
    ('https://lab.passiomatic.com/coldsweat/tests/feed1.xml', 200),
    ('https://lab.passiomatic.com/coldsweat/tests/wrong-feed.xml', 404),
)

@pytest.fixture()
def app():
    app = create_app(config_class=TestingConfig)
    with open(TEST_DIR.joinpath("test-data.sql"), 'r') as f:
        # https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.executescript
        sql = f.read()
        db_wrapper.database.connection().executescript(sql)

    yield app

    db_wrapper.database.connection().close()

@pytest.mark.parametrize("url, status", TEST_FEEDS)
def test_fetcher_status(app, url, status):
    with app.app_context():                
        try:
            response = fetcher.fetch_url(url, timeout=10)
        except RequestException:
            response = None
        assert (response == status) or (response.status_code == status)
