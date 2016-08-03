#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: quick & dirty test suite for Fever API implementation

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''
import sys, subprocess, optparse
from datetime import datetime

from ..utilities import datetime_as_epoch
from ..models import User

TEST_USER_CREDENTIALS = 'test@example.com', 'coldsweat'
ALL = 'groups feeds unread_item_ids saved_item_ids favicons items links unread_recently_read mark_item mark_feed mark_group mark_all'.split()

def run_tests(endpoint, suites=ALL):
    """
    Use curl command line utility to run tests
    """

    epoch = datetime_as_epoch(datetime.utcnow())

    queries = []
    
    if 'groups' in suites:
        queries.extend([
            (False, 'groups')
        ])

    if 'feeds' in suites:
        queries.extend([
            (False, 'feeds')
        ])

    if 'unread' in suites:
        queries.extend([
            (False, 'unread_item_ids')
        ])

    if 'saved' in suites:
        queries.extend([
            (False, 'saved_item_ids')
        ])

    if 'favicons' in suites:
        queries.extend([
            (False, 'favicons')
        ])

    if 'items' in suites:
        queries.extend([
            (False, 'items'),         
            (False, 'items&with_ids=50,51,52'),         
            (False, 'items&max_id=5'),
            (False, 'items&since_id=50')
        ])

    if 'links' in suites:
        queries.extend([
            (False, 'links')                                        # Unsupported
        ])          

    if 'mark_item' in suites:
        queries.extend([
            (True, 'mark=item&as=read&id=1'), 
            (True, 'mark=item&as=read&id=1'),                       # Dupe
            (True, 'mark=item&as=read&id=0'),                       # Does not exist
            (True, 'mark=item&as=unread&id=1'), 
            (True, 'mark=item&as=saved&id=1'), 
            (True, 'mark=item&as=saved&id=1'),                      # Dupe
            (True, 'mark=item&as=saved&id=0'),                      # Does not exist
            (True, 'mark=item&as=unsaved&id=1'), 
        ]) 
        
    if 'mark_feed' in suites:
        queries.extend([
            (True, 'mark=feed&as=read&id=1&before=%d' % epoch), 
            (True, 'mark=feed&as=read&id=1&before=abc'),            # Malformed
            (True, 'mark=blah&as=read&id=1&before=%d' % epoch),     # Malformed (3)
            (True, 'mark=feed&as=read&id=foo&before=abc'),          # Malformed (4)
            (True, 'mark=feed&as_=read&id=1&before=%d' % epoch),    # Malformed (5)
            (True, 'mark=feed&as=read&id=0&before=%d' % epoch),     # Does not exist
        ]) 

    if 'mark_group' in suites:
        queries.extend([
            (True, 'mark=group&as=read&id=1&before=%d' % epoch), 
            (True, 'mark=group&as=read&id=1&before=abc'),           # Malformed 
            (True, 'mark=group&as=read&id=-1&before=%d' % epoch),   # Unsupported
        ]) 

    if 'mark_all' in suites:
        queries.extend([
            (True, 'mark=group&as=read&id=0&before=%d' % epoch),    # Mark all as read 
        ])         

    if 'unread_read' in suites:
        queries.extend([
            (True, 'unread_recently_read=1')
        ])          
                              
    # Test auth failure
    print ('\n= auth (failure)\n')

    subprocess.call([
        "curl", 
        "-dapi_key=%s" % 'wrong-api-key',
        "%s?api&unread_item_ids" % endpoint
    ])
    
    api_key=User.make_api_key(*TEST_USER_CREDENTIALS)

    # Test API commands            
    for as_form, q in queries:
        print ('\n= %s\n' % q)

        if as_form:
            subprocess.call([
                "curl", 
                "-dapi_key=%s" % api_key,
                "-d%s" % q,
                "%s?api" % endpoint
            ])
        else:
            subprocess.call([
                "curl", 
                "-dapi_key=%s" % api_key,
                "%s?api&%s" % (endpoint, q),
            ])
            

parser = optparse.OptionParser(
    usage='%prog endpoint [-s suite]'
    )
parser.add_option(
    '-s', '--suite',
    dest='suite', 
    help='the Fever API test suite to run. Available suites are: groups, feeds, unread, saved, favicons, items, links, unread_read, mark_item, mark_feed mark_group, mark_all')


if __name__ == '__main__':

    options, args = parser.parse_args()

    if not args:
        parser.error("no Fever API endpoint given, e.g.: http://localhost:8080/fever/")
    elif len(args) > 1:
        parser.error("extraneous argument found, use -s suite to run a specific test suite")
        
    suite = options.suite if options.suite else ALL
    
    run_tests(args[0], suite)

