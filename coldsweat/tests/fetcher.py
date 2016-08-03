#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: 

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''
from requests.exceptions import *

from ..fetcher import fetch_url

TEST_FEEDS = (
    (None, 'http://www.aaa.bbb/'),                              # Does not exist
    (200, 'http://www.scripting.com/rss.xml'),                  # First redirect, then 200
    (404, 'http://example.com/wrong-rss.xml'),
)


def run_tests():    
    for expected_status, url in TEST_FEEDS:
        print 'Checking', url, '...'
        try:
            response = fetch_url(url, timeout=5)
        except RequestException:
            response = None
        
        assert (response == expected_status) or (response.status_code == expected_status)
    

if __name__ == '__main__':
    run_tests()

