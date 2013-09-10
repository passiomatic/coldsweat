# -*- coding: utf-8 -*-
"""
Description: Fever API implementation

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
"""
import os, sys, cgi, time, re
from collections import defaultdict
from datetime import datetime
from calendar import timegm

from webob import Response
from webob.exc import HTTPBadRequest

from utilities import *    
from app import *
from models import *
from coldsweat import log

RE_DIGITS = re.compile('[0-9]+')
RECENTLY_READ_DELTA = 60*60 # 1 hour


def groups_command(request, user, result):            
    result.groups = get_groups_for_user(user)
    result.feeds_groups = get_feed_groups_for_user(user)
        
def feeds_command(request, user, result):
    result.feeds = get_feeds_for_user(user)
    result.feeds_groups = get_feed_groups_for_user(user)

def unread_items_command(request, user, result):
    unread_items = get_unread_entries_for_user(user)
    if unread_items:
        result.unread_item_ids = ','.join(map(str,unread_items))
            
def saved_items_command(request, user, result):
    saved_items = get_saved_entries_for_user(user)
    if saved_items:
        result.saved_item_ids = ','.join(map(str,saved_items))

def favicons_command(request, user, result):
    result.favicons = get_icons()

def items_command(request, user, result):

    result.total_items = get_entry_count_for_user(user)

    # From the API: "Use the since_id argument with the highest id 
    #  of locally cached items to request 50 additional items.         
    if 'since_id' in request.GET: 
        try:
            min_id = int(request.GET['since_id'])
            result.items = get_entries_for_user_min(user, min_id)     
        except ValueError:
            pass

        return

    # From the API: "Use the max_id argument with the lowest id of locally 
    #  cached items (or 0 initially) to request 50 previous items.                  
    if 'max_id' in request.GET: 
        try:
            max_id = int(request.GET['max_id'])
            if max_id: 
                result.items = get_entries_for_user_max(user, max_id)            
        except ValueError:
            pass

        return
        
    # From the API: "Use the with_ids argument with a comma-separated list 
    #  of item ids to request (a maximum of 50) specific items."
    if 'with_ids' in request.GET: 
        with_ids = request.GET['with_ids']        
        ids = [int(i) for i in with_ids.split(',') if RE_DIGITS.match(i)]
        result.items = get_entries_for_user(user, ids[:50])
        return
    
    # Unfiltered results
    result.items = get_entries_for_user(user)



def unread_recently_command(request, user, result):    
    log.info('unread_recently_read command is not implemented')
 
    

def mark_command(request, user, result):

    try:
        mark, status, object_id = request.POST['mark'], request.POST['as'], request.POST['id']
    except KeyError:
        return              

    try:        
        object_id = int(object_id)        
    except ValueError:
        return
        
    if mark == 'item':

        try:
            # Sanity check
            entry = Entry.get(Entry.id == object_id)  
        except Entry.DoesNotExist:
            log.debug('could not find requested entry %d, ignored' % object_id)
            return

        if status == 'read':
            try:
                Read.create(user=user, entry=entry)
            except IntegrityError:
                log.debug('entry %d already marked as read, ignored' % object_id)
                return
        #Note: strangely enough 'unread' is not mentioned in 
        #  the Fever API, but Reeder app asks for it
        elif status == 'unread':
            count = Read.delete().where((Read.user==user) & (Read.entry==entry)).execute()
            if not count:
                log.debug('entry %d never marked as read, ignored' % object_id)
                return
        elif status == 'saved':
            try:
                Saved.create(user=user, entry=entry)
            except IntegrityError:
                log.debug('entry %d already marked as saved, ignored' % object_id)
                return
        elif status == 'unsaved':
            count = Saved.delete().where((Saved.user==user) & (Saved.entry==entry)).execute()
            if not count:
                log.debug('entry %d never marked as saved, ignored' % object_id)
                return
                  
        log.debug('marked entry %d as %s' % (object_id, status))


    if mark == 'feed' and status == 'read':

        try:
            # Sanity check
            feed = Feed.get(Feed.id == object_id)  
        except Feed.DoesNotExist:
            log.debug('could not find requested feed %d, ignored' % object_id)
            return

        # Unix timestamp of the the local client’s last items API request
        try:
            before = datetime.utcfromtimestamp(int(request.POST['before']))
        except (KeyError, ValueError):
            return              
        
        q = feed.entries.where(Entry.last_updated_on < before)            
        with transaction():
            for entry in q:
                try:
                    Read.create(user=user, entry=entry)
                except IntegrityError:
                    continue
        
        log.debug('marked feed %d as %s' % (object_id, status))
                

    if mark == 'group' and status == 'read':

        # Unix timestamp of the the local client’s last items API request
        try:
            before = datetime.utcfromtimestamp(int(request.POST['before']))
        except (KeyError, ValueError):
            return              

        # Mark all as read?
        if object_id == 0:                                                
            q = Entry.select().join(Feed).join(Subscription).where(
                (Subscription.user == user) &
                (Entry.last_updated_on < before)
            ).naive()
        else:
            try:        
                group = Group.get(Group.id == object_id)  
            except Group.DoesNotExist:
                log.debug('could not find requested group %d, ignored' % object_id)
                return

            q = Entry.select().join(Feed).join(Subscription).where(
                (Subscription.group == group) & 
                (Subscription.user == user) &
                (Entry.last_updated_on < before)
            ).naive()

        with transaction():
            for entry in q:
                try:
                    Read.create(user=user, entry=entry)
                except IntegrityError:
                    continue
        
        log.debug('marked group %d as %s' % (object_id, status))


def links_command(request, user, result):
    # Hot links (unsupported)
    result.links = []     


COMMANDS = [
    ('groups'                        , groups_command), 
    ('feeds'                         , feeds_command),
    ('items'                         , items_command),
    ('unread_item_ids'               , unread_items_command),
    ('saved_item_ids'                , saved_items_command),
    ('mark'                          , mark_command),
    ('unread_recently_read'          , unread_recently_command),
    ('favicons'                      , favicons_command), 
    ('links'                         , links_command),
]

@view(r'^/fever/?$', 'post')
def endpoint(ctx):

    log.debug('client from %s requested: %s' % (ctx.request.remote_addr, ctx.request.params))
    
    if 'api' not in ctx.request.GET:
        raise HTTPBadRequest()

    result = Struct({'api_version':2, 'auth':0})   
            
    #@@TODO format = 'xml' if request.GET['api'] == 'xml' else 'json'

    if 'api_key' in ctx.request.POST:
        api_key = ctx.request.POST['api_key']        
        try:
            user = User.get((User.api_key == api_key) & (User.is_enabled == True))
        except User.DoesNotExist:
            log.warn('unknown API key %s, unauthorized' % api_key)
            return serialize(result)  #@@TODO: HTTPUnauthorized ?
    else:
        log.warn('missing API key, unauthorized')
        return serialize(result)   #@@TODO: HTTPUnauthorized ?

    # Authorized
    result.auth = 1

    # Note: client *can* send multiple commands at time
    for command, handler in COMMANDS:
        if command in ctx.request.params:            
            handler(ctx.request, user, result)
            #break

    result.last_refreshed_on_time = get_last_refreshed_on_time()

    return serialize(result)


@view(r'^/fever/?$')
@template('fever.html')
def placeholder(ctx):
    pass
    


def serialize(result, format='json'):

    def as_xml(result):
        #@@TODO: implement XML serialization
        raise NotImplementedError

    def as_json(result):
        import json
        return json.dumps(result, indent=4, encoding=ENCODING)

    serializers = {
        'json': as_json,
        'xml': as_xml 
    }
  
    r = Response(content_type='application/json', charset='utf-8')  #application/xml
    r.body = serializers.get(format)(result)   
    return r



# ------------------------------------------------------
# Queries
# ------------------------------------------------------
        
def get_groups_for_user(user):
    q = Group.select().join(Subscription).join(User).where(User.id == user.id).distinct().naive()
    result = [{'id':s.id,'title':s.title} for s in q]
    return result

def get_feeds_for_user(user):
    q = Feed.select().join(Subscription).join(User).where(User.id == user.id).distinct().naive()
    result = []
    for feed in q:

        result.append({
            'id'                  : feed.id,
            'favicon_id'          : feed.icon.id, 
            'title'               : feed.title,
            'url'                 : feed.self_link,
            'site_url'            : feed.alternate_link,
            'is_spark'            : 0, # Unsupported
            'last_updated_on_time': feed.last_updated_on_as_epoch  
        })
    return result        

def get_feed_groups_for_user(user):
    q = Subscription.select().join(User).where(User.id == user.id).distinct().naive()
    groups = defaultdict(lambda: [])
    for s in q:
        groups[s.group.id].append('%d' % s.feed.id)
    result = []
    for g in groups.keys():
        result.append({'group_id':g, 'feed_ids':','.join(groups[g])})
    return result

def get_unread_entries_for_user(user):
    q = Entry.select(Entry.id).join(Feed).join(Subscription).join(User).where(
        (User.id == user.id), 
        ~(Entry.id << Read.select(Read.entry).where(User.id == user.id))).order_by(Entry.id).distinct().naive()
    return [r.id for r in q]

def get_saved_entries_for_user(user):
    q = Entry.select(Entry.id).join(Feed).join(Subscription).join(User).where(
        (User.id == user.id), 
        (Entry.id << Saved.select(Saved.entry).where(User.id == user.id))).order_by(Entry.id).distinct().naive()
    return [r.id for r in q]    

def get_entries_for_user(user, ids=None):

    if ids:
        where_clause = (User.id == user.id) & (Entry.id << ids)
    else:
        where_clause = (User.id == user.id)
    
    #@@TODO: Use Peewee aggregated records instead? http://peewee.readthedocs.org/en/latest/peewee/cookbook.html#aggregating-records
    q = Entry.select().join(Feed).join(Subscription).join(User).where(where_clause).distinct().naive()
    r = Entry.select().join(Read).join(User).where(where_clause).distinct().naive()
    s = Entry.select().join(Saved).join(User).where(where_clause).distinct().naive()

    read_ids = [i.id for i in r]
    saved_ids = [i.id for i in s]

    result = []
    for entry in q:
        result.append({
            'id': entry.id,
            'feed_id': entry.feed.id,
            'title': entry.title,
            'author': entry.author,
            'html': entry.content,
            'url': entry.link,
            'is_saved': 1 if entry.id in saved_ids else 0,
            'is_read': 1 if entry.id in read_ids else 0,
            'created_on_time': entry.last_updated_on_as_epoch
        })
    return result 

def get_entries_for_user_min(user, min_id, bound=50):
    #q = Entry.select().join(Feed).join(Subscription).join(User).where((User.id == user.id) & (Entry.id > min_id)).order_by(Entry.id).distinct().limit(bound).naive()
    q = Entry.select().join(Feed).join(Subscription).join(User).where((User.id == user.id) & (Entry.id > min_id)).distinct().limit(bound).naive()

    r = Entry.select().join(Read).join(User).where((User.id == user.id) & (Entry.id > min_id)).order_by(Entry.id).distinct().naive()
    s = Entry.select().join(Saved).join(User).where((User.id == user.id) & (Entry.id > min_id)).order_by(Entry.id).distinct().naive()

    read_ids = [i.id for i in r]
    saved_ids = [i.id for i in s]

    result = []
    for entry in q:
        result.append({
            'id': entry.id,
            'feed_id': entry.feed.id,
            'title': entry.title,
            'author': entry.author,
            'html': entry.content,
            'url': entry.link,
            'is_saved': 1 if entry.id in saved_ids else 0,
            'is_read': 1 if entry.id in read_ids else 0,
            'created_on_time': entry.last_updated_on_as_epoch 
        })
    return result
    
def get_entries_for_user_max(user, max_id, bound=50):
    #q = Entry.select().join(Feed).join(Subscription).join(User).where((User.id == user.id) & (Entry.id < max_id)).order_by(Entry.id).distinct().limit(bound).naive()
    q = Entry.select().join(Feed).join(Subscription).join(User).where((User.id == user.id) & (Entry.id < max_id)).distinct().limit(bound).naive()

    r = Entry.select().join(Read).join(User).where((User.id == user.id) & (Entry.id < max_id)).order_by(Entry.id).distinct().naive()
    s = Entry.select().join(Saved).join(User).where((User.id == user.id) & (Entry.id < max_id)).order_by(Entry.id).distinct().naive()

    read_ids = [i.id for i in r]
    saved_ids = [i.id for i in s]

    result = []
    for entry in q:
        result.append({
            'id': entry.id,
            'feed_id': entry.feed.id,
            'title': entry.title,
            'author': entry.author,
            'html': entry.content,
            'url': entry.link,
            'is_saved': 1 if entry.id in saved_ids else 0,
            'is_read': 1 if entry.id in read_ids else 0,
            'created_on_time': entry.last_updated_on_as_epoch
        })
    return result    

    
def get_entry_count_for_user(user):
    q = Entry.select().join(Feed).join(Subscription).join(User).where((User.id == user.id)).distinct().count()
    return q

def get_icons():
    """
    Get all the icons
    """
    q = Icon.select()
    
    result = []
    for icon in q:
        result.append({
            'id': icon.id,
            'data': icon.data,
        })
    
    return result
        

def get_last_refreshed_on_time():
    """
    Time of the most recently *refreshed* feed
    """
    last_checked_on = Feed.select().aggregate(fn.Max(Feed.last_checked_on))
    if last_checked_on:        
        return datetime_as_epoch(last_checked_on)
            
    # Return a fallback value
    return datetime_as_epoch(datetime.utcnow())



