# -*- coding: utf-8 -*-
"""
Description: OPML parsing

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
"""

from xml.etree import ElementTree

from ..models import *
from coldsweat import log, favicon
from ..fetcher import add_subscription, add_feed

# Map OPML attr keys to Feed model 
feed_allowed_attribs = {
    'xmlUrl': 'self_link', 
    'htmlUrl': 'alternate_link', 
    'title': 'title',
    'text': 'title', # Alias for title
}

# Map OPML attr keys to Group model 
group_allowed_attribs = {
    'title': 'title',
    'text': 'title', # Alias for title
}

def add_feeds_from_file(source, user):
    """
    Add feeds to database reading from a file containing OPML data. 
    """    
    feeds = []    
    groups = [None] # Use default group
    
    with transaction():

        for event, element in ElementTree.iterparse(source, events=('start','end')):    
            if event == 'start':
                 if (element.tag == 'outline') and ('xmlUrl' not in element.attrib):                    
                    group = Group()

                    #title = element.attrib['text']
                    for k, v in element.attrib.items():
                        if k in group_allowed_attribs:
                            setattr(group, group_allowed_attribs[k], v)
                                
                    #@@NOTE: we could catch an IntegrityError here, but title  
                    #  uniqueness constraint has been added only recently so 
                    #  it is better to avoid that with older installations
                    try:
                        group = Group.get(Group.title==group.title)                    
                    except Group.DoesNotExist:
                        #group = Group(title=title)
                        group.save()                                                                                            
                        groups.append(group)
                        log.debug('added group %s to database' % group.title)

            elif event == 'end':
                if (element.tag == 'outline') and ('xmlUrl' in element.attrib):
                    # We are leaving a feed
                    feed = Feed()
                    
                    for k, v in element.attrib.items():
                        if k in feed_allowed_attribs:
                            setattr(feed, feed_allowed_attribs[k], v)
    
                    feed = add_feed(feed, fetch_icon=True, add_entries=True)    
                    add_subscription(feed, user, groups[len(groups)-1])
                    feeds.append(feed)
                elif element.tag == 'outline':
                    # We are leaving a group
                    groups.pop()
                        
                    
    
    return feeds

            
                        
