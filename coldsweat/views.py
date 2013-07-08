# -*- coding: utf-8 -*-
"""
Description: web views

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""

from webob.exc import HTTPSeeOther, HTTPNotFound, HTTPBadRequest

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

    # Default is unread
    filter_name = 'unread'
    page_title = 'Unread Items' 
    group_id = 0
    
    #@@TODO Grab current session user
    user = User.get((User.username == 'default'))

    r = Entry.select().join(Read).where((Read.user == user)).distinct().naive()
    s = Entry.select().join(Saved).where((Saved.user == user)).distinct().naive()
    read_ids = [i.id for i in r]
    saved_ids = [i.id for i in s]
    
    if 'starred' in ctx.request.GET:
        q = Entry.select().join(Feed).join(Icon).where((Entry.id << Saved.select(Saved.entry))).naive()
        filter_name = 'starred'
        page_title = 'Starred Items'
        #filter_name = 
    elif 'group' in ctx.request.GET:
        group_id = ctx.request.GET['group']   
        try:
            group = Group.get((Group.id == group_id)) 
        except Group.DoesNotExist:
            raise HTTPNotFound('No such group %s' % group_id)
        filter_name = ''
        page_title = group.title                
        # TODO: join(Icon) to reduce number of queries
        q = Entry.select().join(Feed).join(Subscription).where((Subscription.user == user) & (Subscription.group == group)).naive()
    else:
        q = Entry.select().join(Feed).join(Icon).where(~(Entry.id << Read.select(Read.entry))).naive()
            
    entry_count = q.count()
    last_entries = q.order_by(Entry.last_updated_on.desc()).limit(ENTRIES_PER_PAGE).naive()    
    last_checked_on = Feed.select().aggregate(fn.Max(Feed.last_checked_on))
    groups = Group.select().join(Subscription).where(Subscription.user == user).distinct().order_by(Group.title).naive()
            
    page_title = '%s%s' % (page_title, ' (%s)' % entry_count if entry_count else '')
    

    return locals()

@view(r'^/ajax/entries/(\d+)$')
@template('ajax_entry_get.html')
def ajax_entry_get(ctx, entry_id):

    connect()

    try:
        entry = Entry.get((Entry.id == entry_id)) 
    except Entry.DoesNotExist:
        raise HTTPNotFound('No such entry %s' % entry_id)
    
    return locals()
    
@view(r'^/ajax/entries/(\d+)$', method='post')
def ajax_entry_post(ctx, entry_id):

    connect()

    try:
        status = ctx.request.POST['as']
    except KeyError:
        raise HTTPBadRequest('Missing parameter as=read|unread|saved|unsaved')

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
                return
        elif status == 'unread':
            count = Read.delete().where((Read.user==user) & (Read.entry==entry)).execute()
            if not count:
                log.info('entry %d never marked as read, ignored' % entry_id)
                return
        elif status == 'saved':
            try:
                Saved.create(user=user, entry=entry)
            except IntegrityError:
                log.info('entry %s already marked as saved, ignored' % entry_id)
                return
    
        elif status == 'unsaved':
            count = Saved.delete().where((Saved.user==user) & (Saved.entry==entry)).execute()
            if not count:
                log.info('entry %d never marked as saved, ignored' % entry_id)
                return
        
        log.debug('marked entry %s as %s' % (entry_id, status))
    

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


