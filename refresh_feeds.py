#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
#from os import path 
# Make sure Coldsweat package takes precedence
#sys.path.insert(0, path.join(installation_dir, 'coldsweat'))

from coldsweat.models import Feed, connect
from coldsweat import fetcher

if __name__ == '__main__':
    
    connect()
                       
    for feed in Feed.select():
        fetcher.fetch_feed(feed)

                
