#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: base processor tests

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''

import feedparser    

from os import path
from ..markup import BaseProcessor

def run_tests():

    # Figure out current dir
    test_dir = path.dirname(path.abspath(__file__))

    test_files = [
        ('markup/in.xml', 'markup/out.xml'),
    ]

    # Use xhtml_mode to match Feedpaser output
    p = BaseProcessor(xhtml_mode=True)

    for file_in, file_out in test_files:           
        soup_in = feedparser.parse(path.join(test_dir, file_in))
        soup_out = feedparser.parse(path.join(test_dir, file_out))
        for entry_in, entry_out in zip(soup_in.entries, soup_out.entries):    
            p.reset()
            p.feed(entry_in.content[0].value)
            content_out = p.output()
            print '>>>\n', entry_out.content[0].value
            print '<<<\n', content_out
            assert content_out == entry_out.content[0].value
            print entry_in.title, '(OK)'
        


if __name__ == "__main__":
    run_tests()