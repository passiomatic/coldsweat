#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Description: refresh subscriptions feeds.
"""

from coldsweat.models import *
from coldsweat import fetcher

if __name__ == '__main__':
    connect()
    counter = fetcher.fetch_feeds()    
    print '%d feeds checked. See file coldsweat.log for more information.' % counter
