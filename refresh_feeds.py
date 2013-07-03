#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Description: refresh subscriptions feeds.
"""

from coldsweat.models import *
from coldsweat import fetcher

if __name__ == '__main__':
    connect()
    fetcher.fetch_feeds()