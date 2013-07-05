# -*- coding: utf-8 -*-
"""
Description: web views

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""

from webob.exc import HTTPSeeOther, HTTPNotFound

from app import *
from models import *
from utilities import *
import fetcher
from coldsweat import log

ENTRIES_PER_PAGE = 30

@view()
@template('index.html')
def index(ctx):

    connect()

    filter_name = 'Unread Items'

    if 'starred' in ctx.request.GET:
        q = Entry.select().join(Feed).join(Icon).where((Entry.id << Saved.select(Saved.entry)))
        filter_name = 'Starred Items'
    elif 'all' in ctx.request.GET:
        q = Entry.select().join(Feed).join(Icon)
        filter_name = ' Total Items'
    else:
        # Default is unread
        q = Entry.select().join(Feed).join(Icon).where(~(Entry.id << Read.select(Read.entry)))
            
    entry_count = q.count()
    last_entries = q.order_by(Entry.last_updated_on.desc()).limit(ENTRIES_PER_PAGE).naive()

#     r = Entry.select().join(Read).join(User).where(where_clause).distinct().naive()
#     s = Entry.select().join(Saved).join(User).where(where_clause).distinct().naive()
# 
#     read_ids = [i.id for i in r]
#     saved_ids = [i.id for i in s]
        
    last_checked_on = Feed.select().aggregate(fn.Max(Feed.last_checked_on))
        
#     if not entry_count:
#         entry_count = 'Zero'
    
    page_title = '%s %s' % (entry_count if entry_count else 'Zero', filter_name)
    
    #feed_count = Feed.select(Feed.is_enabled==True).count()

    #close()


    return locals()

@view(r'^/ajax/entries/(\d+)$')
@template('ajax_entry_get.js', content_type='application/javascript')
def ajax_entry_get(ctx, entry_id):

    connect()

    try:
        entry = Entry.get((Entry.id == entry_id)) 
    except Entry.DoesNotExist:
        raise HTTPNotFound('No such entry %s' % entry_id)
    
    return locals()
    
@view(r'^/ajax/entries/(\d+)$', method='post')
@template('ajax_entry_post.js', content_type='application/javascript')
def ajax_entry_post(ctx, entry_id):

    connect()

    try:
        status = ctx.request.POST['as']
    except KeyError:
        return              

    try:
        entry = Entry.get((Entry.id == entry_id)) 
    except Entry.DoesNotExist:
        raise HTTPNotFound('No such entry %s' % entry_id)

    #@@TODO Grab current session user
    user = User.get((User.username == 'default'))
    
    if 'mark' in ctx.request.POST:
        if status == 'read':
            try:
                Read.create(user=user, entry=entry)
            except IntegrityError:
                log.info('entry %s already marked as read, ignored' % entry_id)
        
        elif status == 'saved':
            try:
                Saved.create(user=user, entry=entry)
            except IntegrityError:
                log.info('entry %s already marked as saved, ignored' % entry_id)
                return
    
        elif status == 'unsaved':
            pass
        
        log.debug('marked entry %s as %s' % (entry_id, status))
    
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

    with transaction():    
        feed = fetcher.add_feed(self_link, fetch_icon=True)    
        try:
            Subscription.create(user=user, feed=feed, group=default_group)
            set_message(response, u'SUCCESS Feed %s added successfully.' % self_link)            
            log.debug('added feed %s for user %s' % (self_link, username))            
        except IntegrityError:
            set_message(response, u'INFO Feed %s is already in your subscriptions.' % self_link)
            log.info('user %s has already feed %s in her subscriptions' % (username, self_link))    

    #close()
        
    return response


