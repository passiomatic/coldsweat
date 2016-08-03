#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: HTML stripping tests

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''

from ..markup import strip_html

def run_tests():
    tests = [
        ('a', 'a'),                                         # Identity
        ('a <p class="c"><span>b</span></p> a', 'a b a'),        
        (u'à <p class="c"><span>b</span></p> à', u'à b à'), # Unicode
        ('a&amp;a&lt;a&gt;', 'a&a<a>'),                     # Test unescape of entity and char reference too
        ('<span>a</span>', 'a'),
        ('<span>a', 'a'),                                   # Unclosed elements
        ('<p><span>a</p>', 'a'),    
        ('<foo attr=1><bar />a</foo>', 'a'),                # Non HTML tags
    ]
    
    for value, wanted in tests:
        assert strip_html(value) == wanted

if __name__ == "__main__":
    run_tests()