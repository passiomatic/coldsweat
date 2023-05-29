'''
Feed fetcher tests
'''
import pytest
from requests.exceptions import RequestException

from coldsweat.fetcher import fetch_url

TEST_FEEDS = (
    # ('http://www.aaa.bbb/', None),
    # ('https://lab.passiomatic.com/coldsweat/tests/feed1.xml', 200),
    # ('https://lab.passiomatic.com/coldsweat/tests/wrong-feed.xml', 404),
)


@pytest.mark.parametrize("status, url", TEST_FEEDS)
def test_fetcher_status(status, url):
    try:
        response = fetch_url(url, timeout=5)
    except RequestException:
        response = None
    assert (response == status) or (response.status_code == status)
