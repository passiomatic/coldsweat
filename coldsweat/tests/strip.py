#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: HTML stripping tests

Copyright (c) 2013— Andrea Peltrin
License: MIT (see LICENSE.md for details)
'''

from ..markup.html import strip_html

def run_tests():
    tests = [
        ('a <p class="c"><span>b</span></p> a', 'a b a'),        
        ('a&amp;a&lt;a&gt;', 'a&a<a>'), # Test unescape of entity and char reference too
        ('<span>a</span>', 'a'),
        ('<span>a', 'a'),               # Unclosed elements
        ('<p><span>a</p>', 'a'),    
        ('<foo><bar />a</foo>', 'a'),     # Non HTML tags
    ]
    
    for value, wanted in tests:
        assert strip_html(value) == wanted

if __name__ == "__main__":
    run_tests()