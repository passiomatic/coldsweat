#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: feed autodiscovery tests.

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''

from os import path
from ..markup import find_feed_links

def find_feed_link(data, base_url):
    links = find_feed_links(data, base_url)
    if links:        
        return links[0]    
    return None    
    
def run_tests():

    # Figure out current dir
    test_dir = path.dirname(path.abspath(__file__))

    test_files = [
        ('discovery/html5-xhtml.html', 'http://example.com/feed'),
        ('discovery/xhtml.html', 'http://somedomain.com/articles.xml' ),
        ('discovery/html4-base.html', 'http://somedomain.com/articles.xml' ),
        ('discovery/html4-no-base.html', 'http://example.com/articles.xml' ),
    ]
           
    for filename, expected_url in test_files:
        with open(path.join(test_dir, filename)) as f:
            url, title = find_feed_link(f.read(), 'http://example.com')
            assert url == expected_url
            print 'Found', url, title, '(OK)'
        
if __name__ == '__main__':
    run_tests()

