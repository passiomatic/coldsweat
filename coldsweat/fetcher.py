# -*- coding: utf-8 -*-
'''
Description: the feed fetcher

Copyright (c) 2013—2014 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''

import sys, re, time, cgi, urlparse
from os import path
from datetime import datetime
from peewee import IntegrityError

import feedparser
import requests
from requests.exceptions import *

from models import *
from utilities import *
from filters import escape_html
from coldsweat import *
from markup import html

MAX_TITLE_LENGTH = 255
POSITIVE_STATUS_CODES = 200, 302, 304 # Other redirects are handled by Requests

# ------------------------------------------------------
# Entry data
# ------------------------------------------------------

def get_feed_timestamp(soup_feed, default):
    """
    Get the date a feed was last updated
    """
    for header in ['updated_parsed', 'published_parsed']:
        value = soup_feed.get(header, None)
        if value:
            # Fix future dates
            return min(tuple_as_datetime(value), default)
    log.debug('no feed timestamp found, using default')    
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
    log.debug('no entry timestamp found, using default')    
    return default
        
def get_entry_title(entry):
    if 'title' in entry:
        return truncate(html.strip_html(entry.title), MAX_TITLE_LENGTH)
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
    if candidates:
        log.debug('content found for entry %s' % entry.link)    
    if 'summary_detail' in entry:
        log.debug('summary found for entry %s' % entry.link)    
        candidates.append(entry.summary_detail)
    for c in candidates:
        if 'html' in c.type: # Match text/html, application/xhtml+xml
            return c.type, c.value
        else: 
            # If the content is declared to be (or is determined to be) text/plain, 
            #   it will not be sanitized by Feedparser. This is to avoid data loss.
            return c.type, escape_html(c.value)
    log.debug('no content found for entry %s' % entry.link)    
    return 'text/plain', ''

# ------------------------------------------------------
# Add feed and subscription
# ------------------------------------------------------

def add_feed(feed, fetch_icon=False, add_entries=False):
    '''
    Add a feed to database and optionally fetch icon and add entries
    '''

    self_link, alternate_link, title = feed.self_link, feed.alternate_link, feed.title

    try:
        previous_feed = Feed.get(Feed.self_link == self_link)
        log.debug('feed %s has been already added to database, skipped' % self_link)
        return previous_feed
    except Feed.DoesNotExist:
        pass

    if fetch_icon:
        # Prefer alternate_link if available since self_link could 
        #   point to Feed Burner or similar services
        icon_link = alternate_link if alternate_link else self_link    
        (schema, netloc, path, params, query, fragment) = urlparse.urlparse(icon_link)
        icon = Icon.create(data=favicon.fetch(icon_link))
        feed.icon = icon
        log.debug("saved favicon for %s: %s..." % (netloc, icon.data[:70]))    

    #feed.self_link = self_link    
    #feed.title = title 
    feed.save()
    fetch_feed(feed, add_entries)

    return feed
    
def add_subscription(feed, user, group):

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

def fetch_url(url, timeout=None, etag=None, modified_since=None):

    request_headers = {
        'User-Agent': user_agent
    }

    # Conditional GET headers
    if etag and modified_since:
        request_headers['If-None-Match'] = etag
        request_headers['If-Modified-Since'] = format_http_datetime(modified_since)
        
    timeout = timeout if timeout else config.getint('fetcher', 'timeout')
    
    try:
        response = requests.get(url, timeout=timeout, headers=request_headers)
        log.debug("got status %d" % response.status_code)
    except (IOError, RequestException), ex:
        return None
    
    return response


def fetch_feed(feed, add_entries=False):
    
    def post_fetch(status, error=False):
        if status:
            feed.last_status = status
        if error:
            feed.error_count = feed.error_count + 1        
        error_threshold = config.getint('fetcher', 'error_threshold')
        if error_threshold and (feed.error_count > error_threshold):
            feed.is_enabled = False
            feed.last_status = status # Save status code for posterity           
            log.warn("%s has too many errors, disabled" % netloc)        
        feed.save()

    if hasattr(feed, 'subscriptions') and not feed.subscriptions:
        log.debug("feed %s has no subscribers, skipped" % feed.self_link)
        return

    log.debug("fetching %s" % feed.self_link)
           
    schema, netloc, path, params, query, fragment = urlparse.urlparse(feed.self_link)

    now = datetime.utcnow()

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
                      
    response = fetch_url(feed.self_link, etag=feed.etag, modified_since=feed.last_updated_on)
    if not response:
        # Record as "503 Service unavailable"
        post_fetch(503, error=True)
        log.warn("a network error occured while fetching %s" % netloc)
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
            post_fetch(DuplicatedFeedError.code)
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
    elif response.status_code not in POSITIVE_STATUS_CODES:             # No good
        log.warn("%s replied with status %d, aborted" % (netloc, response.status_code))
        post_fetch(response.status_code, error=True)
        return

    soup = feedparser.parse(response.text) 
    # Got parsing error? Log error but do not increment the error counter
    if hasattr(soup, 'bozo') and soup.bozo:
        log.info("%s caused a parser error (%s), tried to parse it anyway" % (netloc, soup.bozo_exception))
        post_fetch(response.status_code, error=False)

    feed.etag = response.headers.get('ETag', None)    
    
    if 'link' in soup.feed:
        feed.alternate_link = soup.feed.link

    # Reset value only if not set before
    if ('title' in soup.feed) and not feed.title:
        feed.title = html.strip_html(soup.feed.title)

    feed.last_updated_on = get_feed_timestamp(soup.feed, now)        
    post_fetch(response.status_code)

    trigger_event('feed_saved', feed)
            
    if not add_entries:    
        return
        
    for parsed_entry in soup.entries:
        
        link = get_entry_link(parsed_entry)
        guid = get_entry_id(parsed_entry, default=link)

        if not guid:
            log.warn('could not find guid for entry from %s, skipped' % netloc)
            continue

        title                = get_entry_title(parsed_entry)
        mime_type, content   = get_entry_content(parsed_entry)
        timestamp            = get_entry_timestamp(parsed_entry, default=now)
        author               = get_entry_author(parsed_entry, soup.feed)
                
        # Skip ancient feed items        
        max_history = config.getint('fetcher', 'max_history')
        if max_history and ((now - timestamp).days > max_history):  
            log.debug("entry %s from %s is over max_history, skipped" % (guid, netloc))
            continue

        try:
            # If entry is already in database with same id, then skip it
            Entry.get(guid=guid)
            log.debug("duplicated entry %s, skipped" % guid)
            continue
        except Entry.DoesNotExist:
            pass

        entry = Entry(
            guid              = guid,
            feed              = feed,
            title             = title,
            author            = author,
            content           = content,
            #@@TODO: add mime_type too
            link              = link,
            last_updated_on   = timestamp
        )
        #events('entry_parsed')(entry, parsed_entry)
        trigger_event('entry_parsed', entry, parsed_entry)
        entry.save()
        #events('entry_saved')(entry)
        trigger_event('entry_saved', entry)

        log.debug(u"added entry %s from %s" % (guid, netloc))


def feed_worker(feed):
    # Allow each process to open and close its database connection    
    connect()
    fetch_feed(feed, add_entries=True)
    close()
    
 
def fetch_feeds():
    """
    Fetch all feeds, possibly parallelizing requests
    """
                       
    start = time.time()

    # Attach feed.subscriptions counter
    q = Feed.select(Feed, fn.Count(Subscription.user).alias('subscriptions')).join(Subscription, JOIN_LEFT_OUTER).group_by(Feed).where(Feed.is_enabled==True)
    
    feeds = list(q)
    if not feeds:
        log.debug("no feeds found to refresh, halted")
        return

    log.debug("starting fetcher")
    trigger_event('fetcher_started')
        
    if config.getboolean('fetcher', 'multiprocessing'):
        from multiprocessing import Pool

        p = Pool(processes=None) # Uses cpu_count()        
        p.map(feed_worker, feeds)

    else:
        # Just sequence requests
        for feed in feeds:
            fetch_feed(feed)
    
    log.info("%d feeds checked in %.2fs" % (len(feeds), time.time() - start))



    