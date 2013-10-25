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
        ('<span>a</span>', 'a'),
        ('a <p class="c"><span>b</span></p> a', 'a b a'),        
        ('a&amp;a&#38;a', 'a&a&a'), # Test unescape of entity and char references too
    ]
    
    for value, wanted in tests:
        assert strip_html(value) == wanted

if __name__ == "__main__":
    run_tests()