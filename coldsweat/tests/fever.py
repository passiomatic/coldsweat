#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Quick & dirty test suite for Fever API implementation
Copyright (c) 2013— Andrea Peltrin
License: MIT (see LICENSE.md for details)

Usage
    python -m coldsweat.tests.fever endpoint

Parameters    
    endpoint: the URL to send Fever API requests, e.g.: http://localhost/coldsweat/fever/

'''
import sys, subprocess
from os import path
from datetime import datetime

from ..utilities import make_md5_hash, datetime_as_epoch
from ..models import User
#from coldsweat import installation_dir


def run_tests(endpoint):
    """
    Use curl command line utility to run tests
    """

    utcnow = datetime.utcnow()

    # Assume to have some test data already fetched
    queries = [
        (False, 'groups'),
        (False, 'feeds'),
        (False, 'unread_item_ids'),
        (False, 'saved_item_ids'),
        (False, 'groups&feeds'),            # Mixed
        (False, 'favicons'),
        (False, 'items?max_id=10'),
        (False, 'items?since_id=5'),
        (False, 'items'), 
        (False, 'links'),                   # Unsupported
        (True, 'unread_recently_read=1'),
        (True, 'mark=item&as=read&id=1'), 
        (True, 'mark=item&as=read&id=1'),   # Dupe
        (True, 'mark=item&as=unread&id=1'), 
        (True, 'mark=item&as=saved&id=1'), 
        (True, 'mark=item&as=saved&id=1'),  # Dupe
        (True, 'mark=item&as=unsaved&id=1'), 
        (True, 'mark=feed&as=read&id=1&before=%d' % datetime_as_epoch(utcnow)), 
        (True, 'mark=group&as=read&id=1&before=%d' % datetime_as_epoch(utcnow)), 
    ]

    username, password = User.DEFAULT_CREDENTIALS    
    api_key=make_md5_hash('%s:%s' % (username, password))

    for as_form, q in queries:
        print ('\n= %s\n' % q)

        if as_form:
            subprocess.call([
                "curl", 
                #"-v",
                "-dapi_key=%s" % api_key,
                "-d%s" % q,
                "%s" % endpoint
            ])
        else:
            subprocess.call([
                "curl", 
                #"-v",
                "-dapi_key=%s" % api_key,
                "%s&%s" % (endpoint, q),
            ])
            

if __name__ == '__main__':

    if len(sys.argv) == 1:
        print __doc__
        sys.exit(1)
    
    _, endpoint = sys.argv
    
    run_tests(endpoint)

