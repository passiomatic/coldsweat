# -*- coding: utf-8 -*-
'''
Description: the feed fetcher

Copyright (c) 2013—2016 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
'''

import sys, os, re, time, urlparse
from datetime import datetime

from peewee import IntegrityError
import feedparser
import requests
from requests.exceptions import *
from webob.exc import *

from coldsweat import *

from plugins import trigger_event

from models import *
from utilities import *

import markup
import filters

__all__ = [
    'Fetcher',
    'validate_url',
    'scrub_url',
    'fetch_url'
]

FETCH_ICONS_DELTA = 30 # Days

class Fetcher(object):
    '''
    Fetch a single given feed
    '''   

    def __init__(self, feed): 
        # Save timestamp for current fetch operation
        self.instant = datetime.utcnow()
        # Extract netloc
        _, self.netloc, _, _, _ = urlparse.urlsplit(feed.self_link)
 
        self.feed = feed

# @@TODO    
#       def handle_500(self, response):
#         '''
#         Internal server error
#         '''
#         pass

    def handle_403(self, response):
        '''
        Forbidden
        '''
        self.feed.error_count   += 1        
        self.feed.last_status   = response.status_code
        logger.warn(u"%s access was denied, skipped" % self.netloc)        
        raise HTTPForbidden
                        
    def handle_404(self, response):
        '''
        Not Found
        '''
        self.feed.error_count   += 1        
        self.feed.last_status   = response.status_code
        logger.warn(u"%s has been not found, skipped" % self.netloc)        
        raise HTTPNotFound
        
    def handle_410(self, response):
        '''
        Gone
        '''
        self.feed.is_enabled    = False
        self.feed.error_count   += 1        
        self.feed.last_status   = response.status_code
        logger.warn(u"%s is gone, disabled" % self.netloc)
        self._synthesize_entry('Feed has been removed from the origin server.')        
        raise HTTPGone
         
    def handle_304(self, response):
        '''
        Not modified
        '''
        self.feed.last_status = response.status_code
        logger.debug(u"%s hasn't been modified, skipped" % self.netloc)               
        raise HTTPNotModified

    def handle_301(self, response):
        '''
        Moved permanently
        '''
        self_link = response.url
            
        try:
            Feed.get(self_link=self_link)
        except Feed.DoesNotExist:
            self.feed.self_link     = self_link                               
            self.feed.last_status   = response.status_code
            logger.info(u"%s has changed its location, updated to %s" % (self.netloc, self_link))
        else:
            self.feed.is_enabled    = False
            self.feed.last_status   = DuplicatedFeedError.code
            self.feed.error_count   += 1             
            self._synthesize_entry('Feed has a duplicated web address.')
            logger.warn(u"new %s location %s is duplicated, disabled" % (self.netloc, self_link))                
            raise DuplicatedFeedError

    def handle_200(self, response):
        '''
        OK plus redirects
        '''
        self.feed.etag   = response.headers.get('ETag', None)
        # Save final status code discarding redirects
        self.feed.last_status = response.status_code

    handle_307 = handle_200 # Alias
    handle_302 = handle_200 # Alias


    def update_feed(self):
                
        logger.debug(u"updating %s" % self.netloc)
               
        # Check freshness
        for value in [self.feed.last_checked_on, self.feed.last_updated_on]:
            if not value:
                continue
            
            # No datetime.timedelta since we need to
            #   deal with large seconds values
            delta = datetime_as_epoch(self.instant) - datetime_as_epoch(value)    
            if delta < config.fetcher.min_interval:
                logger.debug(u"%s is below minimun fetch interval, skipped" % self.netloc)
                return                                      
        
        try:
            response = fetch_url(self.feed.self_link, 
                timeout=config.fetcher.timeout, 
                etag=self.feed.etag, 
                modified_since=self.feed.last_updated_on)
        except RequestException: 
            # Record any network error as 'Service Unavailable'
            self.feed.last_status   =  HTTPServiceUnavailable.code
            self.feed.error_count   += 1   
            logger.warn(u"a network error occured while fetching %s, skipped" % self.netloc)
            self.feed.save()            
            return
    
        self.feed.last_checked_on = self.instant
    
        # Check if we got a redirect first
        if response.history:
            status = response.history[0].status_code
        else:
            status = response.status_code
        
        try:
            handler = getattr(self, 'handle_%d' % status, None)
            if handler:
                handler(response)
            else: 
                self.feed.last_status = status
                logger.warn(u"%s replied with status %d, aborted" % (self.netloc, status))
                return
            self._parse_feed(response.text)
            self._fetch_icon()
        except (HTTPError, HTTPNotModified, DuplicatedFeedError):
            return # Bail out
        finally:
            if config.fetcher.max_errors and self.feed.error_count > config.fetcher.max_errors:
                self._synthesize_entry('Feed has accomulated too many errors (last was %s).' % filters.status_title(status))
                logger.warn(u"%s has accomulated too many errors, disabled" % self.netloc)
                self.feed.is_enabled = False
            self.feed.save()
            
    def update_feed_with_data(self, data):
        self._parse_feed(data)
        self.feed.save()
                      
    def _parse_feed(self, data):

        soup = feedparser.parse(data)         
        # Got parsing error?
        if hasattr(soup, 'bozo') and soup.bozo:
            logger.debug(u"%s caused a parser error (%s), tried to parse it anyway" % (self.netloc, soup.bozo_exception))

        ft = FeedTranslator(soup.feed)
        
        self.feed.last_updated_on    = ft.get_timestamp(self.instant)        
        self.feed.alternate_link     = ft.get_alternate_link()        
        self.feed.title              = self.feed.title or ft.get_title() # Do not set again if already set

        #entries = []
        feed_author = ft.get_author()

        for entry_dict in soup.entries:
    
            t = EntryTranslator(entry_dict)
            
            link = t.get_link()
            guid = t.get_guid(default=link)
    
            if not guid:
                logger.warn(u'could not find GUID for entry from %s, skipped' % self.netloc)
                continue

            timestamp               = t.get_timestamp(self.instant)
            content_type, content   = t.get_content(('text/plain', ''))
        
            # Skip ancient entries        
            if config.fetcher.max_history and (self.instant - timestamp).days > config.fetcher.max_history:
                logger.debug(u"entry %s from %s is over maximum history, skipped" % (guid, self.netloc))
                continue
    
            try:
                # If entry is already in database with same hashed GUID, skip it
                Entry.get(guid_hash=make_sha1_hash(guid)) 
                logger.debug(u"duplicated entry %s, skipped" % guid)
                continue
            except Entry.DoesNotExist:
                pass
    
            entry = Entry(
                feed              = self.feed,                
                guid              = guid,
                link              = link,
                title             = t.get_title(default='Untitled'),
                author            = t.get_author() or feed_author,
                content           = content,
                content_type      = content_type,
                last_updated_on   = timestamp
            )
            
            # At this point we are pretty sure we doesn't have the entry 
            #  already in the database so alert plugins and save data
            trigger_event('entry_parsed', entry, entry_dict)
            entry.save()
            #@@TODO: entries.append(entry)
    
            logger.debug(u"parsed entry %s from %s" % (guid, self.netloc))  
        
        #return entries
        

    def _fetch_icon(self):
    
        if not self.feed.icon or not self.feed.icon_last_updated_on or (self.instant - self.feed.icon_last_updated_on).days > FETCH_ICONS_DELTA:
            # Prefer alternate_link if available since self_link could 
            #   point to Feed Burner or similar services
            self.feed.icon                  = self._google_favicon_fetcher(self.feed.alternate_link or self.feed.self_link)
            self.feed.icon_last_updated_on  = self.instant

            logger.debug(u"fetched favicon %s..." % (self.feed.icon[:70]))    

    
    def _google_favicon_fetcher(self, url):
        '''
        Fetch a site favicon via Google service
        '''
        endpoint = "http://www.google.com/s2/favicons?domain=%s" % urlparse.urlsplit(url).hostname
    
        try:
            response = fetch_url(endpoint)
        except RequestException, exc:
            logger.warn(u"could not fetch favicon for %s (%s)" % (url, exc))
            return Feed.DEFAULT_ICON
    
        return make_data_uri(response.headers['Content-Type'], response.content)


    def add_synthesized_entry(self, title, content_type, content):
        '''
        Create an HTML entry for this feed 
        '''
    
        # Since we don't know the mechanism the feed used to build a GUID for its entries 
        #   synthesize an tag URI from the link and a random string. This makes
        #   entries internally generated by Coldsweat reasonably globally unique

        guid = ENTRY_TAG_URI % (self.instant.year, make_sha1_hash(self.feed.self_link + make_nonce()))
        
        entry = Entry(
            feed              = self.feed,
            guid              = guid,
            title             = title,
            author            = 'Coldsweat',
            content           = content,
            content_type      = content_type,
            last_updated_on   = self.instant
        )
        entry.save()
        logger.debug(u"synthesized entry %s" % guid)    
        return entry
    

    def _synthesize_entry(self, reason):    
        title   = u'This feed has been disabled'
        content = render_template(os.path.join(template_dir, '_entry_feed_disabled.html'), {'reason': reason})
        return self.add_synthesized_entry(title, 'text/html', content)                     
        
        
        
 
class FeedTranslator(object):

    def __init__(self, feed_dict):
        self.feed_dict = feed_dict
        
    def get_timestamp(self, default):
        for header in ['published_parsed', 'updated_parsed']:
            value = self.feed_dict.get(header, None)
            if value:
                # Fix future dates
                return min(tuple_as_datetime(value), default)
        logger.debug(u'no feed timestamp found, using default')    
        return default

    # Nullable fields
    
    def get_author(self):
        if 'name' in self.feed_dict.get('author_detail', []):
            return self.feed_dict.author_detail.name
        return None
    
    def get_alternate_link(self):        
        return self.feed_dict.get('link', None)
        
    def get_title(self):
        if 'title' in self.feed_dict:
            return truncate(markup.strip_html(self.feed_dict.title), Feed.MAX_TITLE_LENGTH)
        return None


class EntryTranslator(object):

    def __init__(self, entry_dict):
        self.entry_dict = entry_dict
    
    def get_guid(self, default):
        """
        Get a useful GUID from a feed entry
        """    
        value = getattr(self.entry_dict, 'id', None)
        return value or default

    def get_timestamp(self, default):
        """
        Select the best timestamp for an entry
        """
        for header in ['published_parsed', 'created_parsed', 'updated_parsed']:
            value = self.entry_dict.get(header, None)
            if value:
                # Fix future dates
                return min(tuple_as_datetime(value), default)
        logger.debug(u'no entry timestamp found, using default')    
        return default
            
    def get_title(self, default):
        if 'title' in self.entry_dict:
            return truncate(markup.strip_html(self.entry_dict.title), Entry.MAX_TITLE_LENGTH)
        return default
    
    def get_content(self, default):
        """
        Select the best content from an entry
        """    
        candidates = self.entry_dict.get('content', [])
        if 'summary_detail' in self.entry_dict:
            candidates.append(self.entry_dict.summary_detail)
        for c in candidates:
            # Match text/html, application/xhtml+xml
            if 'html' in c.type:
                return c.type, c.value
        # Return first result, regardless of MIME type
        if candidates:
            return candidates[0].type, candidates[0].value
    
        logger.debug(u'no entry content found, using default')    
        return default
        
    # Nullable fields
    
    def get_link(self):
        # Special case for FeedBurner entries, see: http://bit.ly/1gRAvJv
        if 'feedburner_origlink' in self.entry_dict:
            return scrub_url(self.entry_dict.feedburner_origlink)
        if 'link' in self.entry_dict:
            return scrub_url(self.entry_dict.link)
        return None
        
    def get_author(self):  
        if 'name' in self.entry_dict.get('author_detail',[]):
            return self.entry_dict.author_detail.name     
        return None


# --------------------
# URL utilities
# --------------------

BLACKLIST_QS = ["utm_source", "utm_campaign", "utm_medium", "utm_content", "utm_cid", "utm_term", "piwik_campaign", "piwik_kwd"]
     
# Lifted from https://github.com/django/django/blob/master/django/core/validators.py
RE_URL = re.compile(
    r'^https?://'                           # http:// or https://
    r'(?:[^:@/]+:[^:@/]+@)?'                # credentials
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
    r'localhost|'                           # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'                            # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)    
    #@@TODO: Add IPv6
    

def validate_url(value):
    return value and RE_URL.search(value)


def scrub_url(url):
    '''
    Clean query string arguments
    '''
    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    d = urlparse.parse_qs(query)
    d = dict((k, v) for k, v in d.items() if k not in BLACKLIST_QS)
    return urlparse.urlunsplit((scheme, netloc, path, urllib.urlencode(d, doseq=True), fragment))


def fetch_url(url, timeout=10, etag=None, modified_since=None):
    '''
    Fecth a given URL optionally issuing a 'Conditional GET' request
    '''

    request_headers = {
        'User-Agent': USER_AGENT
    }

    # Conditional GET headers
    if etag and modified_since:
        request_headers['If-None-Match'] = etag
        request_headers['If-Modified-Since'] = format_http_datetime(modified_since)
        
    try:
        response = requests.get(url, timeout=timeout, headers=request_headers)
    except RequestException, exc:
        logger.debug(u"tried to fetch %s but got %s" % (url, exc.__class__.__name__))
        raise exc
    
    return response

# ------------------------------------------------------
# Custom error codes 9xx & exceptions 
# ------------------------------------------------------

class DuplicatedFeedError(Exception):
    code        = 900
    title       = 'Duplicated feed'
    explanation = 'Feed address matches another already present in the database.'

# Update WebOb status codes map
for klass in (DuplicatedFeedError,): 
    status_map[klass.code] = klass
    
    
def run_tests():
    
    assert scrub_url('http://example.org/feed.xml?utm_source=foo&utm_medium=bar&utm_content=baz&utm_campaign=qux') == 'http://example.org/feed.xml'     
    assert scrub_url('http://example.org/feed.xml?a=1&a=2&b=1&utm_source=foo&utm_medium=bar&utm_content=baz&utm_campaign=qux') == 'http://example.org/feed.xml?a=1&a=2&b=1'
    assert validate_url('https://user.name:password123@example.com/feed.xml')   # OK
    assert validate_url('https://example.com')                                  # OK
    assert validate_url('http://example.org/feed.xml')                          # OK
    assert not validate_url('example.com')                                      # Fail

if __name__ == '__main__':
    run_tests()
