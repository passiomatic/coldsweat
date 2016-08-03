#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: scrub tests

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''

import feedparser    

from os import path
from ..markup import scrub_html

def run_tests():

    # Figure out current dir
    test_dir = path.dirname(path.abspath(__file__))

    blacklist = "feedsportal.com feeds.feedburner.com".split()

    test_files = [
        ('markup/sample1.xml', blacklist[0]),
        ('markup/sample2.xml', blacklist[1]),
    ]

    for filename, unwanted in test_files:           
        soup = feedparser.parse(path.join(test_dir, filename))
        for entry in soup.entries:    
            data = scrub_html(entry.description, blacklist)
            assert data.count(unwanted) == 0
            print entry.title, '(OK)'
        


if __name__ == "__main__":
    run_tests()