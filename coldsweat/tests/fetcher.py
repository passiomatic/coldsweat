#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: 

Copyright (c) 2013—2014 Andrea Peltrin
License: MIT (see LICENSE.md for details)
'''
from ..fetcher import fetch_url, fetch_feed
from ..models import *

TEST_FEEDS = (
    (None, 'http://www.aaa.bbb/'),                              # Does not exist
    (200, 'http://www.scripting.com/rss.xml'),                  # First redirect, then 200
    (404, 'http://example.com/wrong-rss.xml'),
)


def run_tests():    
    # fetch_url tests    
    for expected_status, url in TEST_FEEDS:
        print 'Checking', url, '...'
        response = fetch_url(url, timeout=5)
        if response:
            assert response.status_code == expected_status
    

if __name__ == '__main__':
    run_tests()

