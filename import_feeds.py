#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Description: import a feeds list as OPML file into the Coldsweat database.
"""
from coldsweat.models import *
from coldsweat import opml

if __name__ == '__main__':

    username, password = User.DEFAULT_CREDENTIALS

    connect()
    setup(username, password)

    default_user = User.get(User.username == username)
    default_group = Group.get(Group.title == Group.DEFAULT_GROUP)    
    
    feeds = opml.add_feeds_from_file('./subscriptions.xml', fetch_icons=True)

    with transaction():
        for feed in feeds:         
            Subscription.create(user=default_user, group=default_group, feed=feed)


    close()

                        
