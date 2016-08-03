# -*- coding: utf-8 -*-
"""
Description: Fever API implementation

Copyright (c) 2013—2016 Andrea Peltrin
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
from controllers import *
from models import *

RE_DIGITS           = re.compile('[0-9]+')
RECENTLY_READ_DELTA = 10*60 # 10 minutes
API_VERSION         = 3
COMMANDS = 'groups feeds items unread_item_ids saved_item_ids mark unread_recently_read favicons links'.split()
    
class FeverApp(WSGIApp, FeedController, UserController):

    @POST(r'^/fever/?$')
    def endpoint(self):
        logger.debug(u'client from %s requested: %s' % (self.request.remote_addr, self.request.params))
        
        if 'api' not in self.request.GET:
            raise HTTPBadRequest()
    
        result = Struct({'api_version':API_VERSION, 'auth':0})   
    
        if 'api_key' in self.request.POST:
            api_key = self.request.POST['api_key']        
            user = User.validate_api_key(api_key)
            if not user: 
                logger.warn(u'unknown API key %s, unauthorized' % api_key)
                return self.respond_with_json(result)  
        else:
            logger.warn(u'missing API key, unauthorized')               
            return self.respond_with_json(result)

        # Authorized
        self.user = user        
        result.auth = 1            
            
        # It looks like client *can* send multiple commands at time
        for name in COMMANDS:
            if name in self.request.params:           
                try:
                    handler = getattr(self, '%s_command' % name)
                except AttributeError:
                    logger.debug(u'unrecognized command %s, skipped' % name) 
                    continue        
                handler(result)        
    
        result.last_refreshed_on_time = get_last_refreshed_on_time()
    
        return self.respond_with_json(result)
        
    def respond_with_json(self, data):
        json_data = json.dumps(data, indent=4)
        response = Response(
            json_data, 
            content_type='application/json',
            charset='utf-8')        
        return response

    # ------------------------------------------------------
    # Fever API commands
    # ------------------------------------------------------    
    
    def groups_command(self, result):            
        q = self.get_groups()
        result.groups = [{
            'id'    : group.id, 
            'title' : group.title
        } for group in q]
        result.feeds_groups = get_feed_groups(self.user)
            
    def feeds_command(self, result):
        q = self.get_feeds()
        result.feeds = [{
            'id'                  : feed.id,
            'favicon_id'          : feed.id, 
            'title'               : feed.title,
            'url'                 : feed.self_link,
            'site_url'            : feed.alternate_link,
            'is_spark'            : 0, # Unsupported
            'last_updated_on_time': feed.last_updated_on_as_epoch  
        } for feed in q]        
        result.feeds_groups = get_feed_groups(self.user)
    
    def unread_item_ids_command(self, result):
        q = self.get_unread_entries(Entry.id).naive()        
        ids = [r.id for r in q]
        result.unread_item_ids = ','.join(map(str, ids))
                
    def saved_item_ids_command(self, result):
        q = self.get_saved_entries(Entry.id).naive()
        ids = [r.id for r in q]
        result.saved_item_ids = ','.join(map(str, ids))
    
    def favicons_command(self, result):
        q = Feed.select()
        result.favicons = [{
            'id': feed.id,
            'data': feed.icon_or_default
        } for feed in q]
    
    def items_command(self, result):
    
        result.total_items = self.get_all_entries(Entry.id).count()
    
        # From the API: "Use the since_id argument with the highest id 
        #  of locally cached items to request 50 additional items.         
        if 'since_id' in self.request.GET: 
            try:
                min_id = int(self.request.GET['since_id'])
                result.items = get_entries_min(self.user, min_id)     
            except ValueError:
                pass
    
            return
    
        # From the API: "Use the max_id argument with the lowest id of locally 
        #  cached items (or 0 initially) to request 50 previous items.                  
        if 'max_id' in self.request.GET: 
            try:
                max_id = int(self.request.GET['max_id'])
                if max_id: 
                    result.items = get_entries_max(self.user, max_id)            
            except ValueError:
                pass
    
            return
            
        # From the API: "Use the with_ids argument with a comma-separated list 
        #  of item ids to request (a maximum of 50) specific items."
        if 'with_ids' in self.request.GET: 
            with_ids = self.request.GET['with_ids']        
            ids = [int(i) for i in with_ids.split(',') if RE_DIGITS.match(i)]
            result.items = get_entries(self.user, ids[:50])
            return
        
        # Unfiltered results
        result.items = get_entries(self.user)
    
    
    
    def unread_recently_read_command(self, result):    
        since = datetime.utcnow() - timedelta(seconds=RECENTLY_READ_DELTA)    
        q = Read.delete().where((Read.user==self.user) & (Read.read_on > since)) 
        count = q.execute()
        logger.debug(u'%d entries marked as unread' % count)
     
        
    
    def mark_command(self, result):
    
        try:
            mark, status, object_id = self.request.POST['mark'], self.request.POST['as'], int(self.request.POST['id'])
        except (KeyError, ValueError), ex:
            logger.debug(u'missing or invalid parameter (%s), ignored' % ex)
            return      
    
        if mark == 'item':
    
            try:
                # Sanity check
                entry = Entry.get(Entry.id == object_id)  
            except Entry.DoesNotExist:
                logger.debug(u'could not find entry %d, ignored' % object_id)
                return
    
            if status == 'read':
                try:
                    Read.create(user=self.user, entry=entry)
                except IntegrityError:
                    logger.debug(u'entry %d already marked as read, ignored' % object_id)
                    return
            # Strangely enough 'unread' is not mentioned in 
            #  the Fever API, but Reeder app asks for it
            elif status == 'unread':
                count = Read.delete().where((Read.user==self.user) & (Read.entry==entry)).execute()
                if not count:
                    logger.debug(u'entry %d never marked as read, ignored' % object_id)
                    return
            elif status == 'saved':
                try:
                    Saved.create(user=self.user, entry=entry)
                except IntegrityError:
                    logger.debug(u'entry %d already marked as saved, ignored' % object_id)
                    return
            elif status == 'unsaved':
                count = Saved.delete().where((Saved.user==self.user) & (Saved.entry==entry)).execute()
                if not count:
                    logger.debug(u'entry %d never marked as saved, ignored' % object_id)
                    return
                      
            logger.debug(u'marked entry %d as %s' % (object_id, status))
    
    
        elif mark == 'feed' and status == 'read':
    
            try:
                # Sanity check
                feed = Feed.get(Feed.id == object_id)  
            except Feed.DoesNotExist:
                logger.debug(u'could not find feed %d, ignored' % object_id)
                return
    
            # Unix timestamp of the the local client’s last items API request
            try:
                before = datetime.utcfromtimestamp(int(self.request.POST['before']))
            except (KeyError, ValueError), ex:
                logger.debug(u'missing or invalid parameter (%s), ignored' % ex)
                return              
            
            q = Entry.select(Entry).join(Feed).join(Subscription).where(
                (Subscription.user == self.user) &
                (Subscription.feed == feed) & 
                # Exclude entries already marked as read
                ~(Entry.id << Read.select(Read.entry).where(Read.user == self.user)) &
                # Exclude entries fetched after last sync
                (Entry.last_updated_on < before)
            ).distinct().naive()
    
            with transaction():
                for entry in q:
                    try:
                        Read.create(user=self.user, entry=entry)
                    except IntegrityError:
                        # Should not happen, due to the query above, log as warning
                        logger.warn(u'entry %d already marked as read, ignored' % entry.id)
                        continue
            
            logger.debug(u'marked feed %d as %s' % (object_id, status))
                    
    
        elif mark == 'group' and status == 'read':
    
            # Unix timestamp of the the local client’s 'last items' API request
            try:
                before = datetime.utcfromtimestamp(int(self.request.POST['before']))
            except (KeyError, ValueError), ex:
                logger.debug(u'missing or invalid parameter (%s), ignored' % ex)
                return              
    
            # Mark all as read?
            if object_id == 0:                                                
                q = Entry.select(Entry).join(Feed).join(Subscription).where(
                    (Subscription.user == self.user) &
                    # Exclude entries already marked as read
                    ~(Entry.id << Read.select(Read.entry).where(Read.user == self.user)) &
                    # Exclude entries fetched after last sync
                    (Entry.last_updated_on < before)
                ).distinct().naive()
            else:
                try:        
                    group = Group.get(Group.id == object_id)  
                except Group.DoesNotExist:
                    logger.debug(u'could not find group %d, ignored' % object_id)
                    return
    
                q = Entry.select(Entry).join(Feed).join(Subscription).where(
                    (Subscription.user == self.user) &
                    (Subscription.group == group) & 
                    # Exclude entries already marked as read
                    ~(Entry.id << Read.select(Read.entry).where(Read.user == self.user)) &
                    # Exclude entries fetched after last sync
                    (Entry.last_updated_on < before)
                ).distinct().naive()
    
            with transaction():
                for entry in q:                
                    try:
                        Read.create(user=self.user, entry=entry)
                    except IntegrityError:
                        # Should not happen thanks to the query above, log as warning
                        logger.warn(u'entry %d already marked as read, ignored' % entry.id)
                        continue
            
            logger.debug(u'marked group %d as %s' % (object_id, status))
    
        else:   
            logger.debug(u'malformed mark command (mark %s (%s) as %s ), ignored' % (mark, object_id, status))
    
    
    
    def links_command(self, result):
        # Hot links (unsupported)
        result.links = []     

def setup_app():
    return FeverApp()

# ------------------------------------------------------
# Specific Fever queries
# ------------------------------------------------------
        
def get_feed_groups(user):
    q = Subscription.select(Subscription, Feed, Group).join(Feed).switch(Subscription).join(Group).where(Subscription.user == user)
    groups = defaultdict(lambda: [])
    for s in q:
        groups[s.group.id].append(str(s.feed.id))
    result = []
    for g in groups:
        result.append({'group_id':g, 'feed_ids':','.join(groups[g])})
    return result


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


def get_last_refreshed_on_time():
    """
    Time of the most recently *refreshed* feed
    """
    last_checked_on = Feed.select().aggregate(fn.Max(Feed.last_checked_on))
    if last_checked_on:        
        return datetime_as_epoch(last_checked_on)
            
    # Return a fallback value
    return datetime_as_epoch(datetime.utcnow())

