# -*- coding: utf-8 -*-
'''
Description: the feed fetcher

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''

import sys, os, re, time, cgi, urlparse
from datetime import datetime

import feedparser
import requests
from requests.exceptions import RequestException

from models import *
from utilities import *
from coldsweat import *


def get_feed_updated(feed, default):
    """
    Get the date a feed was last updated
    """
    for header in ['updated_parsed', 'published_parsed']:
        value = feed.get(header, None)
        if value:
            # Fix future dates
            return min(tuple_as_datetime(value), default)
    return default

def get_entry_timestamp(entry, default):
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
        return entry.title
    return "Untitled"
    
def get_entry_id(entry):
    """
    Get a useful id from a feed entry
    """    
    if ('id' in entry) and entry.id: 
        #if type(entry.id) is dict:
        #    return entry.id.values()[0]
        return entry.id

    if 'link' in entry: 
        return entry.link
    content = get_entry_content(entry)
    if content: 
        return make_sha1_hash(content)
    if 'title' in entry: 
        return make_sha1_hash(entry.title)

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

def add_feed(self_link, alternate_link=None, title=None, fetch_icon=False, fetch_entries=False):

    try:
        previous_feed = Feed.get(Feed.self_link == self_link)
        log.debug('feed %s has been already added' % self_link)
        return previous_feed
    except Feed.DoesNotExist:
        pass

    feed = Feed()            

    feed.self_link = self_link
    feed.alternate_link = alternate_link 
    feed.title = title 

    (schema, netloc, path, params, query, fragment) = urlparse.urlparse(feed.self_link)
    
    if fetch_icon:
        icon = Icon.create(data=favicon.fetch(self_link))
        feed.icon = icon
        log.debug("saved favicon for %s: %s..." % (netloc, icon.data[:70]))    

    feed.save()

    if fetch_entries:
        fetch_feed(feed)

    return feed
    
def fetch_feed(feed):
    
    def post_fetch(status, error=False):
        if status:
            feed.last_status = status
        if error:
            feed.error_count = feed.error_count + 1        
        if feed.error_count > config.getint('fetcher', 'error_threshold'):
            feed.is_enabled = False
            log.warn("%s has too many errors, disabled" % netloc)
        feed.save()

    if not feed.is_enabled:
        log.info("feed %s is disabled, skipped" % feed.self_link)
        return

    log.debug("fetching %s" % feed.self_link)
           
    (schema, netloc, path, params, query, fragment) = urlparse.urlparse(feed.self_link)

    now = datetime.utcnow()

    headers = {
        'User-Agent': DEFAULT_USER_AGENT #@@TODO: config.get('fetcher', 'user_agent') if config.has_option('fetcher', 'user_agent') else DEFAULT_USER_AGENT
    }

    if feed.last_checked_on:
        if (now - feed.last_checked_on).seconds < config.getint('fetcher', 'min_interval'):
            log.debug("last_checked_on for %s is below min_interval, skipped" % netloc)
            return

    if feed.last_updated_on:
        if (now - feed.last_updated_on).seconds < config.getint('fetcher', 'min_interval'):
            log.debug("last_updated_on for %s is below min_interval, skipped" % netloc)
            return
       
    # Conditional GET headers
    if feed.etag and feed.last_updated_on:
        headers['If-None-Match'] = feed.etag
        headers['If-Modified-Since'] = format_http_datetime(feed.last_updated_on)
            
    try:
        response = requests.get(feed.self_link, timeout=config.getint('fetcher', 'timeout'), headers=headers)
    except RequestException:
        # Interpret as 'Service Unavailable'
        post_fetch(503, error=True)
        log.error("a network error occured while fetching %s, skipped" % netloc)
        return

    feed.last_checked_on = now

    if response.status_code == 304: # Not modified
        log.debug("%s hasn't been modified, skipped" % netloc)
        post_fetch(response.status_code)
        return
    elif response.status_code == 410: # Gone
        log.info("%s is gone, disabled" % netloc)
        feed.is_enabled = False
        post_fetch(response.status_code)
        return
    if response.status_code == 301: # Moved permanently
        log.info("%s has changed location, updated" % netloc)
        feed.self_link = response.url
    elif response.status_code not in [200, 302, 307]:
        log.warn("%s replied with status %d, aborted" % (netloc, response.status_code))
        post_fetch(response.status_code, error=True)
        return

    try:
        soup = feedparser.parse(response.text) 
    except Exception, exc:
        log.error("could not parse %s (%s)" % (feed.self_link, exc))
        post_fetch(response.status_code, error=True)
        return

    feed.etag = response.headers.get('ETag', None)    
     
    if 'link' in soup.feed:
        feed.alternate_link = soup.feed.link

    if 'title' in soup.feed:
        feed.title = soup.feed.title

    feed.last_updated_on = get_feed_updated(soup.feed, now)    
    #feed.last_status = response.status_code
    
    post_fetch(response.status_code)
    

    #@@TODO: under the same transaction ? 
    for entry in soup.entries:
        timestamp = get_entry_timestamp(entry, now)

        guid = get_entry_id(entry)
                
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
        
        d = {
            'guid'              : guid,
            'feed'              : feed,
            'title'             : get_entry_title(entry),
            'author'            : get_entry_author(entry, soup.feed),
            'content'           : content,
            'link'              : entry.link,
            'last_updated_on'   : timestamp,         
        }

        # Save to database
        Entry.create(**d)

        log.debug(u"added entry '%s'" % entry.title)
 

def fetch_feeds(force_all=False):
    """
    Fetch all feeds, possibly parallelizing requests
    """
                       
    start = time.time()

    #@@TODO: honor force_all arg
    
    feeds = Feed.select()
    
    multiprocessing = config.getboolean('fetcher', 'multiprocessing')     
    if multiprocessing:
        from multiprocessing import Pool
        processes = config.getint('fetcher', 'processes')        
        log.debug("starting fetcher with %d workers" % processes)

        p = Pool(processes)        
        p.map(fetch_feed, feeds, config.getint('fetcher', 'chunk_size'))

    else:
        log.debug("starting fetcher")
        # Just sequence requests
        for feed in feeds:
            fetch_feed(feed)
    
    log.info("%d feeds fetched in %fs" % (feeds.count(), time.time() - start))

    