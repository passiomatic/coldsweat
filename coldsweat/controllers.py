# -*- coding: utf-8 -*-
'''
Description: controllers

Copyright (c) 2013—2016 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
'''

import sys, os, re, time, urlparse
from datetime import datetime
from xml.etree import ElementTree

from peewee import JOIN_LEFT_OUTER, fn, IntegrityError
import feedparser
import requests
from requests.exceptions import *
from webob.exc import *

from models import *
from utilities import *
from plugins import trigger_event, load_plugins
from filters import escape_html, status_title
from coldsweat import *
from fetcher import *


class BaseController(object):

    def __init__(self):
        connect()
        
    def __del__(self):
        close()

class UserController(BaseController):
    '''
    Base user controller class. Derived classes may need to override the user property
    '''
    
    @property
    def user(self):
        return self._current_user
    
    @user.setter
    def user(self, user):
        self._current_user = user    
        
    def add_subscription(self, feed, group):
        '''
        Associate a feed/group pair to current user
        '''
        try:
            subscription = Subscription.create(user=self.user, feed=feed, group=group)
        except IntegrityError:
            logger.debug(u'user %s already has feed %s in her subscriptions' % (self.user.username, feed.self_link))    
            return None
    
        logger.debug(u'subscribed user %s to feed %s' % (self.user.username, feed.self_link))                
        return subscription    

    def remove_subscription(self, feed):
        '''
        Remove a feed subscription for current user
        '''
        Subscription.delete().where((Subscription.user == self.user) & (Subscription.feed == feed)).execute()


    # ------------------------------------------------------
    # Queries
    # ------------------------------------------------------ 

    # Entries
            
    def mark_entry(self, entry, status):
        '''
        Mark an entry as read|unread|saved|unsaved for current user
        '''
        if status == 'read':
            try:
                Read.create(user=self.user, entry=entry)
            except IntegrityError:
                logger.debug(u'entry %s already marked as read, ignored' % entry.id)
                return
        elif status == 'unread':
            count = Read.delete().where((Read.user==self.user) & (Read.entry==entry)).execute()
            if not count:
                logger.debug(u'entry %s never marked as read, ignored' % entry.id)
                return
        elif status == 'saved':
            try:
                Saved.create(user=self.user, entry=entry)
            except IntegrityError:
                logger.debug(u'entry %s already saved, ignored' % entry.id)
                return
        elif status == 'unsaved':
            count = Saved.delete().where((Saved.user==self.user) & (Saved.entry==entry)).execute()
            if not count:
                logger.debug(u'entry %s never saved, ignored' % entry.id)
                return
        
        logger.debug(u'entry %s %s' % (entry.id, status))
     
    def get_unread_entries(self, *select):         
        #@@TODO: include saved information too
        q = _q(*select).where((Subscription.user == self.user) &
            ~(Entry.id << Read.select(Read.entry).where(Read.user == self.user))).distinct()
        return q
    
    def get_saved_entries(self, *select):   
        #@@TODO: include read information too
        q = _q(*select).where((Subscription.user == self.user) & 
            (Entry.id << Saved.select(Saved.entry).where(Saved.user == self.user))).distinct()
        return q
    
    def get_all_entries(self, *select):     
        #@@TODO: include read and saved information too
        q = _q(*select).where(Subscription.user == self.user).distinct()
        return q    
    
    def get_group_entries(self, group, *select):     
        #@@TODO: include read and saved information too
        q = _q(*select).where((Subscription.user == self.user) & (Subscription.group == group))
        return q
        
    def get_feed_entries(self, feed, *select):     
        #@@TODO: include read and saved information too
        q = _q(*select).where((Subscription.user == self.user) & (Subscription.feed == feed)).distinct()
        return q

    # Feeds
    
    def get_feeds(self, *select):  
        select = select or [Feed, fn.Count(Entry.id).alias('entry_count')]
        q = Feed.select(*select).join(Entry, JOIN_LEFT_OUTER).switch(Feed).join(Subscription).where(Subscription.user == self.user).group_by(Feed)
        return q  

    def get_group_feeds(self, group):
        q = Feed.select().join(Subscription).where((Subscription.user == self.user) & (Subscription.group == group))
        return q
    
    # Groups
    
    def get_groups(self):     
        q = Group.select().join(Subscription).where(Subscription.user == self.user).distinct().order_by(Group.title) 
        return q   


 # Shortcut
def _q(*select):
    select = select or (Entry, Feed)
    q = Entry.select(*select).join(Feed).join(Subscription)
    return q     




class FeedController(BaseController):
    '''
    Feed controller class
    '''
    
    def add_feed_from_url(self, self_link, fetch_data=False):
        '''
        Save a new feed object to database via its URL
        '''
        feed = Feed(self_link=self_link)
        return self.add_feed(feed, fetch_data)


    def add_feed(self, feed, fetch_data=False):
        '''
        Save a new feed object to database
        '''
        feed.self_link = scrub_url(feed.self_link)

        try:
            previous_feed = Feed.get(self_link_hash=make_sha1_hash(feed.self_link))
            logger.debug(u'feed %s has been already added to database, skipped' % feed.self_link)
            return previous_feed
        except Feed.DoesNotExist:
            pass

        feed.save()        
        if fetch_data:
            self.fetch_feeds([feed])
        return feed

#     #@@TODO:  delete feed if there are no subscribers
#     def remove_feed(self, feed):
#         pass


    def add_feeds_from_file(self, filename, fetch_data=False):
        """
        Add feeds to database reading from a file containing OPML data. 
        """    
    
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
    
        default_group = Group.get(Group.title == Group.DEFAULT_GROUP)    
    
        feeds = []    
        groups = [default_group]
    
    
        for event, element in ElementTree.iterparse(filename, events=('start','end')):
            if event == 'start':
                 if (element.tag == 'outline') and ('xmlUrl' not in element.attrib):
                    # Entering a group
                    group = Group()
    
                    for k, v in element.attrib.items():
                        if k in group_allowed_attribs:
                            setattr(group, group_allowed_attribs[k], v)
    
                    try:
                        group = Group.get(Group.title==group.title)
                    except Group.DoesNotExist:
                        group.save()
                        logger.debug(u'added group %s to database' % group.title)
    
                    groups.append(group)
    
            elif event == 'end':
                if (element.tag == 'outline') and ('xmlUrl' in element.attrib):
    
                    # Leaving a feed
                    feed = Feed()
    
                    for k, v in element.attrib.items():
                        if k in feed_allowed_attribs:
                            setattr(feed, feed_allowed_attribs[k], v)
    
                    
                    feed = self.add_feed(feed, fetch_data)  
                    feeds.append((feed, groups[-1]))
                elif element.tag == 'outline':
                    # Leaving a group
                    groups.pop()
        return feeds
        

    # ------------------------------------------------------
    # Fetching
    # ------------------------------------------------------  

    def fetch_feeds(self, feeds):
        """
        Fetch given feeds, possibly parallelizing requests
        """
        
        start = time.time()
        
        load_plugins()
    
        logger.debug(u"starting fetcher")
        trigger_event('fetch_started')
            
        if config.fetcher.processes:
            from multiprocessing import Pool
            # Each worker has its own connection
            p = Pool(config.fetcher.processes, initializer=connect)
            p.map(feed_worker, feeds)
            # Exit the worker processes so their connections do not leak
            p.close()
        else:
            # Just sequence requests in this process
            for feed in feeds:
                feed_worker(feed)
        
        trigger_event('fetch_done', feeds)
        
        logger.info(u"%d feeds checked in %.2fs" % (len(feeds), time.time() - start))        
        

    def fetch_all_feeds(self):
        """
        Fetch all enabled feeds, possibly parallelizing requests
        """
    
        q = Feed.select().where(Feed.is_enabled==True)
        
        feeds = list(q)
        if not feeds:
            logger.debug(u"no feeds found to fetch, halted")
            return
    
        self.fetch_feeds(feeds)


def feed_worker(feed):
    fetcher = Fetcher(feed)
    fetcher.update_feed()

        
        



