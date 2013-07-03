#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Description: refresh all subscrptions feeds.
"""

from coldsweat.models import Feed, connect, close
from coldsweat import fetcher

if __name__ == '__main__':
    
    connect()
                       
    for feed in Feed.select():
        fetcher.fetch_feed(feed)

    close()