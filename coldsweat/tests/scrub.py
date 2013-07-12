#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: scrub tests

Copyright (c) 2013— Andrea Peltrin
License: MIT (see LICENSE.md for details)
'''

import feedparser    

from os import path
from ..html import scrub_entry

def run_tests():

    # Figure out current dir
    test_dir = path.dirname(path.abspath(__file__))

    blacklist = "feeds.feedburner.com feedsportal.com".split()

    test_files = [
        ('scrub/macrumors.xml', blacklist[0]),
        ('scrub/dotnetmagazine.xml', blacklist[1]),
    ]

    for filename, unwanted in test_files:           
        soup = feedparser.parse(path.join(test_dir, filename))
        for entry in soup.entries:    
            data = scrub_entry(entry.description, blacklist)
            assert data.count(unwanted) == 0
            print entry.title, '(OK)'
        


if __name__ == "__main__":
    run_tests()