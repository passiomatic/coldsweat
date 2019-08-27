#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: HTML stripping tests

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''
import pytest

from coldsweat.markup import strip_html


@pytest.mark.parametrize("value, wanted", [
        ('a', 'a'),  # Identity
        ('a <p class="c"><span>b</span></p> a', 'a b a'),
        (u'à <p class="c"><span>b</span></p> à', u'à b à'),  # Unicode
        ('a&amp;a&lt;a&gt;',
            'a&a<a>'),  # Test unescape of entity and char reference too
        ('<span>a</span>', 'a'),
        ('<span>a', 'a'),  # Unclosed elements
        ('<p><span>a</p>', 'a'),
        ('<foo attr=1><bar />a</foo>', 'a'),  # Non HTML tags
    ]
    )
def test_stripping_html(value, wanted):
    assert strip_html(value) == wanted
