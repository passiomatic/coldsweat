#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: 

Copyright (c) 2013—2014 Andrea Peltrin
License: MIT (see LICENSE.md for details)
'''
from ..fetcher import check_url, fetch_feed
from ..models import *

TEST_FEEDS = (
    (503, 'http://www.aaa.bbb/'),                               # Does not exist
    (200, 'http://www.scripting.com/rss.xml'),                  # First redirect, then 200
    (404, 'http://www.markboulton.co.uk/journal/rss_atom/'),
    (200, 'http://feeds.feedburner.com/codinghorror'),
)


def run_tests():    
    # check_url tests    
    for expected_status, url in TEST_FEEDS:
        print 'Checking', url
        assert check_url(url, timeout=5) == expected_status
    

if __name__ == '__main__':
    run_tests()

