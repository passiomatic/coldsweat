# -*- coding: utf-8 -*-
'''
Description: extracts links from entries to compute Fever 'Hot Links'

Copyright (c) 2014— Andrea Peltrin
License: MIT (see LICENSE for details)
'''
from datetime import datetime, timedelta
import urlparse
from requests.exceptions import RequestException

from coldsweat import *
from coldsweat.models import *
from coldsweat.markup import html
from coldsweat.utilities import * 
from coldsweat.filters import friendly_url

timeout = config.getint('fetcher', 'timeout')                                

@event('entry_saved')
def saved(entry):    
    if 'html' not in entry.content_type:
        return # Could not parse this
    
    urls = html.find_links(entry.content)
    # Add the entry itself also to cope with 'linked lists' feeds 
    #   ala Pinboard/Popular. That is, link is never referenced in the
    #   entry content but it is used directly as the entry link    
    if entry.link:
        urls.append(entry.link)
    
    for url in urls:
        url = scrub_url(url, scrub_fragments=True)

        try:
            # In most cases after expansion we end up having
            #   url == expanded_url, so be it
            link = Link.create(url=url, expanded_url=url) 
        except IntegrityError:
            link = Link.get(Link.url_hash==make_sha1_hash(url))
            
        try:
            # Save a link reference for current entry
            reference = Reference.create(entry=entry, link=link)
        except IntegrityError:
            pass

@event('fetch_started')
def started():  
    pass
        
@event('fetch_done')
def done(feeds):
    when = datetime.utcnow() - timedelta(hours=12)    
    
    # Attempt to expand any recently collected links. This allow
    #   to fetch again any link which caused a connection error in
    #   a previous fecth.
    q = Link.select().where((Link.created_on > when) and (Link.last_status == None))
    for link in q:
        try:
            response = fetch_url(link.url, timeout=timeout)
        except RequestException:
            continue # Try later

        if response.status_code == 200:
            link.expanded_url = scrub_url(response.url)
            try:
                content_type = response.headers['Content-Type']
            except KeyError:
                content_type = ''
                            
            if 'html' in content_type:
                link.title = truncate(html.find_title(response.text)) or friendly_url(link.expanded_url)
            else:
                link.title = friendly_url(link.expanded_url)
        else:
            logger.warn(u'fetched link %s but got status %d' % (link.url, response.status_code))

        link.last_status = response.status_code
        link.save()
        
        
    

