#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: title finder tests

Copyright (c) 2014— Andrea Peltrin
License: MIT (see LICENSE for details)
'''

import feedparser    

from os import path
from ..markup.html import find_title

def run_tests():

    # Figure out current dir
    test_dir = path.dirname(path.abspath(__file__))

    test_files = [
        ('markup/title-ok.html', 'Android L’s app design—early looks at YouTube, Gmail, Maps, and more | Ars Technica'),
        ('markup/title-ko.html', ''),
    ]

    for filename, wanted in test_files:           
        data = open(path.join(test_dir, filename)).read()
        title = find_title(data)
        assert title == wanted
        print title, '(OK)'
        


if __name__ == "__main__":
    run_tests()