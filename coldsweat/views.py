# -*- coding: utf-8 -*-
"""
Description: web views

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""

from app import *
from models import *
import fetcher
from webob.exc import HTTPSeeOther 

from coldsweat import log

from tempita import HTMLTemplate


@view()
@template('index.html')
def index(ctx):

    connect()

    #@@TODO: remove read entries from list                                                
    last_entries = Entry.select().join(Feed).join(Icon).order_by(Entry.last_updated_on.desc()).limit(5)
        
    q = Feed.select(fn.Max(Feed.last_checked_on))
    if q.exists():
        last_checked_on = q.scalar()
    else:
        last_checked_on = '–'
        
    unread_count = Entry.select().where(~(Entry.id << Read.select(Read.entry))).naive().count()
    if not unread_count:
        unread_count = '–'
    
    feed_count = Feed.select(Feed.is_enabled==True).count()

    coldsweat_db.close()


    return locals()
    

@view(method='post')
def index_post(ctx):     

    connect()
    
    # Redirect
    response = HTTPSeeOther(location=ctx.request.url)
    
    self_link, username, password = ctx.request.POST['self_link'], ctx.request.POST['username'], ctx.request.POST['password']

    try:
        #@@TODO: user = get_auth_user(username, password)
        user = User.get((User.username == username) & (User.password == password) & (User.is_enabled == True)) 
    except User.DoesNotExist:
        set_message(response, u'ERROR Wrong username or password, please check your credentials.')            
        return response
                
    default_group = Group.get(Group.title==Group.DEFAULT_GROUP)

    with coldsweat_db.transaction():    
        feed = fetcher.add_feed(self_link, fetch_icon=True)    
        try:
            Subscription.create(user=user, feed=feed, group=default_group)
            set_message(response, u'SUCCESS Feed %s added successfully.' % self_link)            
            log.debug('added feed %s for user %s' % (self_link, username))            
        except IntegrityError:
            set_message(response, u'INFO Feed %s is already in your subscriptions.' % self_link)
            log.info('user %s has already feed %s in her subscriptions' % (username, self_link))    

    coldsweat_db.close()
        
    return response


# def get_stats():
#     pass
    

