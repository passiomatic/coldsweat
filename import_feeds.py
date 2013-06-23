#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Description: import a feeds list as OPML file into the Coldsweat database.
"""
from coldsweat.models import *
from coldsweat import opml

if __name__ == '__main__':

    connect()
    setup(skip_if_existing=True)

    username, password = User.DEFAULT_CREDENTIALS

    default_user = User.get(User.username == username)
    default_group = Group.get(Group.title == Group.DEFAULT_GROUP)    
    
    feeds = opml.add_feeds_from_file('./subscriptions.xml')

    with coldsweat_db.transaction():
        for feed in feeds:         
            Subscription.create(user=default_user, group=default_group, feed=feed)


            
                        
