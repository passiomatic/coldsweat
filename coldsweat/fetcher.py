# -*- coding: utf-8 -*-
'''
Description: the feed fetcher

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''

import sys, re, time, cgi, urlparse
from os import path
from datetime import datetime

import feedparser
import requests
from requests.exceptions import *

from markup import html
from models import *
from utilities import *
from coldsweat import *

# ------------------------------------------------------
# Blacklist
# ------------------------------------------------------

blacklist = []    
def load_blacklist(filename):
    try:
        with open(filename) as f:
            for line in f:
                if line == '\n' or line.startswith('#') or line.startswith(';'):
                    continue # Skip empty values and comments
                
                blacklist.append(line.rstrip('\n'))
    except IOError:
        log.warn("could not load %s" % filename)

# ------------------------------------------------------
# Entry data
# ------------------------------------------------------

def get_feed_timestamp(feed, default):
    """
    Get the date a feed was last updated
    """
    for header in ['updated_parsed', 'published_parsed']:
        value = feed.get(header, None)
        if value:
            # Fix future dates
            return min(tuple_as_datetime(value), default)
    return default

def get_entry_timestamp(entry, default=None):
    """
    Select the best timestamp for an entry
    """
    for header in ['updated_parsed', 'published_parsed', 'created_parsed']:
        value = entry.get(header, None)
        if value:
            # Fix future dates
            return min(tuple_as_datetime(value), default)
    return default
        
def get_entry_title(entry):
    if 'title' in entry:
        return entry.title #@@ Strip HTML
    return 'Untitled'

def get_entry_link(entry):
    # Special case for Feedburner entries, see: http://bit.ly/1gRAvJv
    if 'feedburner_origlink' in entry:
        return entry.feedburner_origlink
    if 'link' in entry:    
        return entry.link
    return None

    
def get_entry_id(entry, default=None):
    """
    Get a useful id from a feed entry
    """    
    if ('id' in entry) and entry.id: 
        return entry.id
    return default
    
def get_entry_author(entry, feed):
    """
    Divine authorship
    """

    if 'name' in entry.get('author_detail',[]):
        return entry.author_detail.name     
    elif 'name' in feed.get('author_detail', []):
        return feed.author_detail.name
    return None

def get_entry_content(entry):
    """
    Select the best content from an entry
    """

    candidates = entry.get('content', [])
    if 'summary_detail' in entry:
        candidates.append(entry.summary_detail)
    for c in candidates:
        if 'html' in c.type: 
            return c.value
    if candidates:
        return candidates[0].value
    return ''

# ------------------------------------------------------
# Add feed and subscription
# ------------------------------------------------------

def add_feed(self_link, title='', fetch_icon=False, add_entries=False):
    '''
    Add a feed to database and optionally fetch icon and add entries
    '''

    try:
        previous_feed = Feed.get(Feed.self_link == self_link)
        log.debug('feed %s has been already added, skipped' % self_link)
        return previous_feed
    except Feed.DoesNotExist:
        pass

    feed = Feed()            

    if fetch_icon:
        # Prefer alternate_link if available since self_link could 
        #   point to Feed Burner or similar services
        #@@TODO icon_link = alternate_link if alternate_link else self_link    
        icon_link = self_link    
        (schema, netloc, path, params, query, fragment) = urlparse.urlparse(icon_link)
        icon = Icon.create(data=favicon.fetch(icon_link))
        feed.icon = icon
        log.debug("saved favicon for %s: %s..." % (netloc, icon.data[:70]))    

    feed.self_link = self_link    
    feed.title = title 
    feed.save()

    fetch_feed(feed, add_entries)

    return feed
    
def add_subscription(feed, user, group=None):

    if not group:
        group = Group.get(Group.title == Group.DEFAULT_GROUP)    

    try:
        subscription = Subscription.create(user=user, feed=feed, group=group)
    except IntegrityError:
        log.debug('user %s has already feed %s in her subscriptions' % (user.username, feed.self_link))    
        return None

    log.debug('added feed %s for user %s' % (feed.self_link, user.username))                
    return subscription
    
# ------------------------------------------------------
# Feed fetching and parsing 
# ------------------------------------------------------

def check_url(url, timeout=None, etag=None, modified_since=None):
    '''
    Issue an HEAD - and if it fails a GET - to the given URL
    '''
    
    schema, netloc, path, params, query, fragment = urlparse.urlparse(url)
    
    request_headers = {
        'User-Agent': user_agent
    }

    # Conditional GET/HEAD headers
    if etag and modified_on:
        request_headers['If-None-Match'] = etag
        request_headers['If-Modified-Since'] = format_http_datetime(modified_since)
        
    timeout = timeout if timeout else config.getint('fetcher', 'timeout')
    
    for method, r in [('HEAD', requests.head), ('GET', requests.get)]:
        try:
            log.debug("checking %s with %s" % (netloc, method))
            response = r(url, timeout=timeout, headers=request_headers)
            status = response.status_code
            log.debug("got status %d" % status)
            if status in (200, 304):
                break
        except (IOError, RequestException):
            # Interpret as 'Service Unavailable'
            log.warn("a network error occured while checking %s" % netloc)
            status = 503
    
    return status


def fetch_feed(feed, add_entries=False):
    
    def post_fetch(status, error=False):
        if status:
            feed.last_status = status
        if error:
            feed.error_count = feed.error_count + 1        
        if feed.error_count > config.getint('fetcher', 'error_threshold'):
            feed.is_enabled = False
            log.warn("%s has too many errors, disabled" % netloc)        
        feed.save()

    log.debug("fetching %s" % feed.self_link)
           
    schema, netloc, path, params, query, fragment = urlparse.urlparse(feed.self_link)

    now = datetime.utcnow()

    request_headers = {
        'User-Agent': user_agent
    }

    interval = config.getint('fetcher', 'min_interval')

    # Check freshness
    for fieldname in ['last_checked_on', 'last_updated_on']:
        value = getattr(feed, fieldname)
        if not value:
            continue

        # No datetime.timedelta since we need to deal with large seconds values            
        delta = datetime_as_epoch(now) - datetime_as_epoch(value)    
        if delta < interval:
            log.debug("%s for %s is below min_interval, skipped" % (fieldname, netloc))
            return            
                      
    # Conditional GET headers
    if feed.etag and feed.last_updated_on:
        request_headers['If-None-Match'] = feed.etag
        request_headers['If-Modified-Since'] = format_http_datetime(feed.last_updated_on)

    timeout = config.getint('fetcher', 'timeout')
                
    try:
        response = requests.get(feed.self_link, timeout=timeout, headers=request_headers)
    except (IOError, RequestException):
        # Interpret as 'Service Unavailable'
        post_fetch(503, error=True)
        log.warn("a network error occured while fetching %s, skipped" % netloc)
        return

    feed.last_checked_on = now

    if response.history and response.history[0].status_code == 301:     # Moved permanently        
        self_link = response.url
        
        try:
            Feed.get(self_link=self_link)
        except Feed.DoesNotExist:
            feed.self_link = self_link                               
            log.info("%s has changed its location, updated to %s" % (netloc, self_link))
        else:
            feed.is_enabled = False
            log.warn("new %s location %s is duplicated, disabled" % (netloc, self_link))                
            # Save final status for posterity
            post_fetch(response.status_code)
            return

    if response.status_code == 304:                                     # Not modified
        log.debug("%s hasn't been modified, skipped" % netloc)
        post_fetch(response.status_code)
        return
    elif response.status_code == 410:                                   # Gone
        log.warn("%s is gone, disabled" % netloc)
        feed.is_enabled = False
        post_fetch(response.status_code)
        return
    elif response.status_code not in (200, ):                           # No good
        log.warn("%s replied with status %d, aborted" % (netloc, response.status_code))
        post_fetch(response.status_code, error=True)
        return

    soup = feedparser.parse(response.text) #, response_headers=response.headers)
    # Got parsing error?     
    if hasattr(soup, 'bozo') and soup.bozo:
        log.warn("could not parse %s (%s), aborted" % (netloc, soup.bozo_exception))
        post_fetch(response.status_code, error=True)
        return

    feed.etag = response.headers.get('ETag', None)    
    
    if 'link' in soup.feed:
        feed.alternate_link = soup.feed.link

    # Reset value only if not set before
    if ('title' in soup.feed) and not feed.title:
        feed.title = soup.feed.title #@@TODO Strip HTML

    feed.last_updated_on = get_feed_timestamp(soup.feed, now)        
    post_fetch(response.status_code)
    
    if not add_entries:    
        return
        
    for entry in soup.entries:
        
        link        = get_entry_link(entry)
        guid        = get_entry_id(entry, default=link)

        if not guid:
            log.warn('could not find guid for entry from %s, skipped' % netloc)
            continue

        title       = get_entry_title(entry)
        timestamp   = get_entry_timestamp(entry, default=now)
        author      = get_entry_author(entry, soup.feed)
                
        # Skip ancient feed items        
        if (now - timestamp).days > config.getint('fetcher', 'max_history'):  
            log.debug("entry %s from %s is over max_history, skipped" % (guid, netloc))
            continue

        try:
            # If entry is already in database with same id, then skip it
            Entry.get(guid=guid)
            log.debug("duplicated entry %s, skipped" % guid)
            continue
        except Entry.DoesNotExist:
            pass

        content = get_entry_content(entry)
        if blacklist:
            content = html.scrub_entry(content, blacklist)

        d = {
            'guid'              : guid,
            'feed'              : feed,
            'title'             : title,
            'author'            : author,
            'content'           : content,
            'link'              : link,
            'last_updated_on'   : timestamp,         
        }

        # Save to database
        Entry.create(**d)

        log.debug(u"added entry %s from %s" % (guid, netloc))


def feed_worker(feed):
    # Allow each process to open and close its database connection    
    connect()
    fetch_feed(feed, add_entries=True)
    close()
    
 
def fetch_feeds(force_all=False):
    """
    Fetch all feeds, possibly parallelizing requests
    """
                       
    start = time.time()

    if config.getboolean('fetcher', 'scrub'):
        load_blacklist(path.join(installation_dir, 'etc/blacklist'))
        log.debug("loaded blacklist: %s" % ', '.join(blacklist))
        
    if force_all:
        q = Feed.select()
    else:
        q = Feed.select().where(Feed.is_enabled==True)
    
    feeds = list(q)
    if not feeds:
        log.debug("no feeds found to refresh, halted")
        return

    log.debug("starting fetcher (force_all is %s)" % ('on' if force_all else 'off'))
        
    if config.getboolean('fetcher', 'multiprocessing'):
        from multiprocessing import Pool

        p = Pool(processes=None) # Uses cpu_count()        
        p.map(feed_worker, feeds)

    else:
        # Just sequence requests
        for feed in feeds:
            fetch_feed(feed)
    
    log.info("%d feeds checked in %fs" % (len(feeds), time.time() - start))



    