# -*- coding: utf-8 -*-
'''
Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''
import pytest
from requests.exceptions import RequestException

from coldsweat.fetcher import fetch_url

TEST_FEEDS = (
    #(None, 'http://www.aaa.bbb/'),
    #(200, 'http://www.scripting.com/rss.xml'),
    #(404, 'http://example.com/wrong-rss.xml'),
)


@pytest.mark.parametrize("status,url", TEST_FEEDS)
def test_fetcher(status, url):
    print('Checking', url, '...')
    try:
        response = fetch_url(url, timeout=5)
    except RequestException:
        response = None
    assert (response == status) or (response.status_code == status)
