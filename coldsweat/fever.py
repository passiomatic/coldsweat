# -*- coding: utf-8 -*-
"""
Description: Fever API implementation

Copyright (c) 2013—2014 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
"""
import re, json
from collections import defaultdict
from datetime import datetime, timedelta

from webob import Request, Response
from webob.exc import *
from peewee import fn, IntegrityError

from coldsweat import *
from utilities import *    
from app import *
from models import *

RE_DIGITS           = re.compile('[0-9]+')
RECENTLY_READ_DELTA = 10*60 # 10 minutes
API_VERSION         = 3
    
class FeverApp(WSGIApp):

    @POST(r'^/fever/?$')
    def endpoint(self):
        logger.debug('client from %s requested: %s' % (self.request.remote_addr, self.request.params))
        
        if 'api' not in self.request.GET:
            raise HTTPBadRequest()
    
        result = Struct({'api_version':API_VERSION, 'auth':0})   
    
        if 'api_key' in self.request.POST:
            api_key = self.request.POST['api_key']        
            user = User.validate_api_key(api_key)
            if not user: 
                logger.warn('unknown API key %s, unauthorized' % api_key)
                return self.respond_with_json(result)  
        else:
            logger.warn('missing API key, unauthorized')               
            return self.respond_with_json(result)
    
        # Authorized
        result.auth = 1
    
        # It looks like client *can* send multiple commands at time
        for command, handler in COMMANDS:
            if command in self.request.params:            
                handler(self.request, user, result)
    
        result.last_refreshed_on_time = get_last_refreshed_on_time()
    
        return self.respond_with_json(result)

    def respond_with_json(self, data):
        json_data = json.dumps(data, indent=4)
        response = Response(
            json_data, 
            content_type='application/json',
            charset='utf-8')        
        return response

    @staticmethod
    def setup():
        return FeverApp()

# ------------------------------------------------------
# Fever API commands
# ------------------------------------------------------    

def groups_command(request, user, result):            
    result.groups = get_groups(user)
    result.feeds_groups = get_feed_groups(user)
        
def feeds_command(request, user, result):
    result.feeds = get_feeds(user)
    result.feeds_groups = get_feed_groups(user)

def unread_items_command(request, user, result):
    unread_items = get_unread_entries(user)
    result.unread_item_ids = ''
    if unread_items:
        result.unread_item_ids = ','.join(map(str,unread_items))
            
def saved_items_command(request, user, result):
    saved_items = get_saved_entries(user)
    result.saved_item_ids = ''
    if saved_items:
        result.saved_item_ids = ','.join(map(str,saved_items))

def favicons_command(request, user, result):
    result.favicons = get_icons()

def items_command(request, user, result):

    result.total_items = get_entry_count(user)

    # From the API: "Use the since_id argument with the highest id 
    #  of locally cached items to request 50 additional items.         
    if 'since_id' in request.GET: 
        try:
            min_id = int(request.GET['since_id'])
            result.items = get_entries_min(user, min_id)     
        except ValueError:
            pass

        return

    # From the API: "Use the max_id argument with the lowest id of locally 
    #  cached items (or 0 initially) to request 50 previous items.                  
    if 'max_id' in request.GET: 
        try:
            max_id = int(request.GET['max_id'])
            if max_id: 
                result.items = get_entries_max(user, max_id)            
        except ValueError:
            pass

        return
        
    # From the API: "Use the with_ids argument with a comma-separated list 
    #  of item ids to request (a maximum of 50) specific items."
    if 'with_ids' in request.GET: 
        with_ids = request.GET['with_ids']        
        ids = [int(i) for i in with_ids.split(',') if RE_DIGITS.match(i)]
        result.items = get_entries(user, ids[:50])
        return
    
    # Unfiltered results
    result.items = get_entries(user)



def unread_recently_command(request, user, result):    
    since = datetime.utcnow() - timedelta(seconds=RECENTLY_READ_DELTA)    
    q = Read.delete().where((Read.user==user) & (Read.read_on > since)) 
    count = q.execute()
    logger.debug('%d entries marked as unread' % count)
 
    

def mark_command(request, user, result):

    try:
        mark, status, object_id = request.POST['mark'], request.POST['as'], int(request.POST['id'])
    except (KeyError, ValueError), ex:
        logger.debug('missing or invalid parameter (%s), ignored' % ex)
        return      

    if mark == 'item':

        try:
            # Sanity check
            entry = Entry.get(Entry.id == object_id)  
        except Entry.DoesNotExist:
            logger.debug('could not find entry %d, ignored' % object_id)
            return

        if status == 'read':
            try:
                Read.create(user=user, entry=entry)
            except IntegrityError:
                logger.debug('entry %d already marked as read, ignored' % object_id)
                return
        # Strangely enough 'unread' is not mentioned in 
        #  the Fever API, but Reeder app asks for it
        elif status == 'unread':
            count = Read.delete().where((Read.user==user) & (Read.entry==entry)).execute()
            if not count:
                logger.debug('entry %d never marked as read, ignored' % object_id)
                return
        elif status == 'saved':
            try:
                Saved.create(user=user, entry=entry)
            except IntegrityError:
                logger.debug('entry %d already marked as saved, ignored' % object_id)
                return
        elif status == 'unsaved':
            count = Saved.delete().where((Saved.user==user) & (Saved.entry==entry)).execute()
            if not count:
                logger.debug('entry %d never marked as saved, ignored' % object_id)
                return
                  
        logger.debug('marked entry %d as %s' % (object_id, status))


    elif mark == 'feed' and status == 'read':

        try:
            # Sanity check
            feed = Feed.get(Feed.id == object_id)  
        except Feed.DoesNotExist:
            logger.debug('could not find feed %d, ignored' % object_id)
            return

        # Unix timestamp of the the local client’s last items API request
        try:
            before = datetime.utcfromtimestamp(int(request.POST['before']))
        except (KeyError, ValueError), ex:
            logger.debug('missing or invalid parameter (%s), ignored' % ex)
            return              
        
        q = Entry.select(Entry).join(Feed).join(Subscription).where(
            (Subscription.user == user) &
            (Subscription.feed == feed) & 
            # Exclude entries already marked as read
            ~(Entry.id << Read.select(Read.entry).where(Read.user == user)) &
            # Exclude entries fetched after last sync
            (Entry.last_updated_on < before)
        ).distinct().naive()

        with transaction():
            for entry in q:
                try:
                    Read.create(user=user, entry=entry)
                except IntegrityError:
                    # Should not happen, due to the query above, log as warning
                    logger.warn('entry %d already marked as read, ignored' % entry.id)
                    continue
        
        logger.debug('marked feed %d as %s' % (object_id, status))
                

    elif mark == 'group' and status == 'read':

        # Unix timestamp of the the local client’s 'last items' API request
        try:
            before = datetime.utcfromtimestamp(int(request.POST['before']))
        except (KeyError, ValueError), ex:
            logger.debug('missing or invalid parameter (%s), ignored' % ex)
            return              

        # Mark all as read?
        if object_id == 0:                                                
            q = Entry.select(Entry).join(Feed).join(Subscription).where(
                (Subscription.user == user) &
                # Exclude entries already marked as read
                ~(Entry.id << Read.select(Read.entry).where(Read.user == user)) &
                # Exclude entries fetched after last sync
                (Entry.last_updated_on < before)
            ).distinct().naive()
        else:
            try:        
                group = Group.get(Group.id == object_id)  
            except Group.DoesNotExist:
                logger.debug('could not find group %d, ignored' % object_id)
                return

            q = Entry.select(Entry).join(Feed).join(Subscription).where(
                (Subscription.user == user) &
                (Subscription.group == group) & 
                # Exclude entries already marked as read
                ~(Entry.id << Read.select(Read.entry).where(Read.user == user)) &
                # Exclude entries fetched after last sync
                (Entry.last_updated_on < before)
            ).distinct().naive()

        #@@TODO: Use insert_many()
        with transaction():
            for entry in q:                
                try:
                    Read.create(user=user, entry=entry)
                except IntegrityError:
                    # Should not happen thanks to the query above, log as warning
                    logger.warn('entry %d already marked as read, ignored' % entry.id)
                    continue
        
        logger.debug('marked group %d as %s' % (object_id, status))

    else:   
        logger.debug('malformed mark command (mark %s (%s) as %s ), ignored' % (mark, object_id, status))



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

# ------------------------------------------------------
# Queries
# ------------------------------------------------------
        
def get_groups(user):
    q = Group.select().join(Subscription).where(Subscription.user == user).distinct()
    result = [{'id':g.id,'title':g.title} for g in q]
    return result

def get_feeds(user):
    q = Feed.select(Feed).join(Subscription).where(Subscription.user == user).distinct()
    result = []
    for feed in q:

        result.append({
            'id'                  : feed.id,
            'favicon_id'          : feed.id, 
            'title'               : feed.title,
            'url'                 : feed.self_link,
            'site_url'            : feed.alternate_link,
            'is_spark'            : 0, # Unsupported
            'last_updated_on_time': feed.last_updated_on_as_epoch  
        })
    return result        

def get_feed_groups(user):
    q = Subscription.select(Subscription, Feed, Group).join(Feed).switch(Subscription).join(Group).where(Subscription.user == user)
    groups = defaultdict(lambda: [])
    for s in q:
        groups[s.group.id].append(str(s.feed.id))
    result = []
    for g in groups:
        result.append({'group_id':g, 'feed_ids':','.join(groups[g])})
    return result

def get_unread_entries(user):
    q = Entry.select(Entry.id).join(Feed).join(Subscription).where(
        (Subscription.user == user) &  
        ~(Entry.id << Read.select(Read.entry).where(Read.user == user))).distinct().naive()
    return [r.id for r in q]

def get_saved_entries(user):
    q = Entry.select(Entry.id).join(Feed).join(Subscription).where(
        (Subscription.user == user) &  
        (Entry.id << Saved.select(Saved.entry).where(Saved.user == user))).distinct().naive()
    return [s.id for s in q]    


def _get_entries(user, q):

    r = Entry.select(Entry.id).join(Read).where(Read.user == user).naive()
    s = Entry.select(Entry.id).join(Saved).where(Saved.user == user).naive()
    
    read_ids    = dict((i.id, None) for i in r)
    saved_ids   = dict((i.id, None) for i in s)
    
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
    
def get_entries(user, ids=None):

    if ids:
        where_clause = (Subscription.user == user) & (Entry.id << ids)
    else:
        where_clause = (Subscription.user == user)
    
    q = Entry.select(Entry, Feed).join(Feed).join(Subscription).where(where_clause).distinct()
    return _get_entries(user, q) 

def get_entries_min(user, min_id, bound=50):
    q = Entry.select(Entry, Feed).join(Feed).join(Subscription).where((Subscription.user == user) & (Entry.id > min_id)).distinct().limit(bound)
    return _get_entries(user, q) 

def get_entries_max(user, max_id, bound=50):
    q = Entry.select(Entry, Feed).join(Feed).join(Subscription).where((Subscription.user == user) & (Entry.id < max_id)).distinct().limit(bound)
    return _get_entries(user, q) 

def get_entry_count(user):
    return Entry.select().join(Feed).join(Subscription).where(Subscription.user == user).distinct().count()


def get_icons():
    """
    Get all the feed icons
    """
    q = Feed.select()
    
    result = []
    for feed in q:
        result.append({
            'id': feed.id,
            'data': feed.icon if feed.icon else Feed.DEFAULT_ICON,
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

