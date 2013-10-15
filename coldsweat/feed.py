# -*- coding: utf-8 -*-
'''
Description: feed utilities

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''

import urlparse

from models import *
from coldsweat import *

def add_feed(self_link, alternate_link=None, title=None, fetch_icon=False, fetch_entries=False):
    '''
    Add a feed to database and optionally fetch icon and entries
    '''

    try:
        previous_feed = Feed.get(Feed.self_link == self_link)
        log.debug('feed %s has been already added, skipped' % self_link)
        return previous_feed
    except Feed.DoesNotExist:
        pass

    feed = Feed()            

    if fetch_icon:
        # Prefer alternate_link if available since self_link could 
        #   point to Feed Burner or similar services
        icon_link = alternate_link if alternate_link else self_link    
        (schema, netloc, path, params, query, fragment) = urlparse.urlparse(icon_link)
        icon = Icon.create(data=favicon.fetch(icon_link))
        feed.icon = icon
        log.debug("saved favicon for %s: %s..." % (netloc, icon.data[:70]))    

    feed.self_link = self_link
    feed.alternate_link = alternate_link 
    feed.title = title 

    feed.save()

    if fetch_entries:
        fetch_feed(feed)

    return feed
    
def add_subscription(feed, user, group=None):

    if not group:
        group = Group.get(Group.title == Group.DEFAULT_GROUP)    

    try:
        subscription = Subscription.create(user=user, feed=feed, group=group)
    except IntegrityError:
        log.debug('user %s has already feed %s in her subscriptions' % (user.username, feed.self_link))    
        return None
    
    return subscription

