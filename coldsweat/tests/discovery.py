#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: feed autodiscovery tests.

Copyright (c) 2013— Andrea Peltrin
License: MIT (see LICENSE.md for details)
'''

from os import path
from ..discovery import get_link

def run_tests():

    # Figure out current dir
    test_dir = path.dirname(path.abspath(__file__))

    test_files = [
        ('discovery/html5-xhtml.html', 'http://example.com/feed'),
        ('discovery/xhtml.html', 'http://somedomain.com/articles.xml' ),
        ('discovery/html4-base.html', 'http://somedomain.com/articles.xml' ),
    ]
           
    for filename, expected_url in test_files:
        with open(path.join(test_dir, filename)) as f:
            url = get_link(f.read(), 'http://example.com')
            assert url == expected_url
            print 'Found', url, '(OK)'
        

if __name__ == '__main__':
    run_tests()

