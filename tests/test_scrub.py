#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: scrub tests

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''

import feedparser
import pytest

from os import path

from coldsweat.markup import scrub_html

blacklist = "feedsportal.com feeds.feedburner.com".split()


@pytest.mark.parametrize("filename, unwanted", [
 ('markup/sample1.xml', blacklist[0]),
 ('markup/sample1.xml', blacklist[1])
    ])
def test_scrub(filename, unwanted):

    # Figure out current dir
    test_dir = path.dirname(path.abspath(__file__))
    soup = feedparser.parse(path.join(test_dir, filename))
    for entry in soup.entries:
        data = scrub_html(entry.description, blacklist)
        assert data.count(unwanted) == 0
        print(entry.title, '(OK)')
