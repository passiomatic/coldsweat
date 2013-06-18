# -*- coding: utf-8 -*-
"""
Description: Fever API implementation

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
"""
import os, sys, cgi, time, re
from collections import defaultdict
from calendar import timegm

from utilities import *    
from app import *
from models import *

from sqlite3 import IntegrityError

import logging
log = logging.getLogger()

RE_DIGITS = re.compile('[0-9]+')
RECENTLY_READ_DELTA = 60*60 # 1 hour

# -------------------
# Fever API
# -------------------


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
    
    
    pass


def mark_command(request, user, result):

    try:
        mark = request.POST['mark']
        entry_status = request.POST['as']
        entry_id = int(request.POST['id'])        
    except KeyError, ValueError:
        return              

    if entry_status not in ['saved', 'unsaved', 'read']:
        return
    
    #now = datetime.utcnow()
        
    if mark == 'item':

        try:
            entry = Entry.get(Entry.id == entry_id) # Sanity check 
        except Entry.DoesNotExist:
            log.warn('could not find requested entry %d, ignored' % entry_id)
            return

        if entry_status == 'read':
            try:
                Read.create(user=user, entry=entry)
            except IntegrityError:
                log.warn('entry %d already marked as read, ignored' % entry_id)
                return
        elif entry_status == 'saved':
            try:
                Saved.create(user=user, entry=entry)
            except IntegrityError:
                log.warn('entry %d already marked as saved, ignored' % entry_id)
                return
        elif entry_status == 'unsaved':
            count = Saved.delete().where((User.id==user.id) & (Entry.id==entry_id)).execute()
            if not count:
                log.warn('entry %d never marked as saved, ignored' % entry_id)
                return
                  
        log.debug('marked entry %d as %s' % (entry_id, entry_status))


    #@@TODO: mark:feed, mark:group


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
    ('unread_recently_read_command'  , unread_recently_command),
    ('favicons'                      , favicons_command), 
    ('links'                         , links_command),
]

@view(r'^/fever/$', 'POST')
def endpoint(request, _):

    log.debug('client request -> %s' % request.params)

    result = Struct({'api_version':2, 'auth':0})    
    
    if 'api' not in request.GET:
        return HTTP_OK, headers, serialize(result) # Ignore request
        
    #@@TODO format = 'xml' if request.GET['api'] == 'xml' else 'json'

    headers = [('Content-Type', 'application/json')] # application/xml
        
    if 'api_key' in request.POST:
        api_key = request.POST['api_key']        
        try:
            user = User.get((User.api_key == api_key) & (User.is_enabled == True))
        except User.DoesNotExist:
            return HTTP_UNAUTHORIZED, headers, serialize(result) 
    else:
        return HTTP_UNAUTHORIZED, headers, serialize(result)   

    # Authorized
    result.auth = 1

    # Note: client *can* send multiple commands at time
    for command, handler in COMMANDS:
        if command in request.params:            
            handler(request, user, result)
            #break

    result.last_refreshed_on_time = get_last_refreshed_on_time()
       
    return HTTP_OK, headers, serialize(result)



def serialize(result, format='json'):

    def as_xml(result):
        #@@TODO: implement XML serialization
        raise NotImplementedError

    def as_json(result):
        import json
        #json_result = json.dumps(result, sort_keys=True, indent=4, encoding=ENCODING)
        return json.dumps(result, indent=4, encoding=ENCODING)

    serializers = {
        'json': as_json,
        'xml': as_xml 
    }

    return serializers.get(format)(result)



# ------------------------------------------------------
# Queries
# ------------------------------------------------------
        
def get_groups_for_user(user):
    q = Group.select(Group).join(Subscription).join(User).where(User.id == user.id).distinct().naive()
    result = [{'id':s.id,'title':s.title} for s in q]
    return result

def get_feed_groups_for_user(user):
    q = Subscription.select(Subscription).join(User).where(User.id == user.id).distinct().naive()
    groups = defaultdict(lambda: [])
    for s in q:
        groups[str(s.group.id)].append('%d' % s.feed.id)
    result = []
    for g in groups.keys():
        result.append({'group':g, 'feed_ids':','.join(groups[g])})
    return result

def get_feeds_for_user(user):
    q = Feed.select(Feed).join(Subscription).join(User).where(User.id == user.id).distinct().naive()
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
    #@@TODO
    #q = Feed.select(fn.Max(Feed.last_checked_on).alias('last_checked_on'))
    
    return int(time.time()) # timegm(value.utctimetuple())


# if __name__ == '__main__':
#     pass


