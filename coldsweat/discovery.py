# -*- coding: utf-8 -*-
"""
Description: find the feed for a web page 

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2006 Aaron Swartz
Portions are copyright (c) 2002–4 Mark Pilgrim

Code derived from feedfinder <http://www.aaronsw.com/2002/feedfinder/>
"""


from sgmllib import SGMLParser, charref
import  urllib, urlparse, re, sys

from coldsweat import log

FEED_TYPES = [
    'application/rss+xml',
    'text/xml',
    'application/atom+xml',
    'application/x.atom+xml',
    'application/x-atom+xml'
]
    
class BaseParser(SGMLParser):
    def __init__(self, base_url):
        SGMLParser.__init__(self)
        self.links = []
        self.base_url = base_url
        
    def normalize_attrs(self, attrs):
        def clean_attr(v):
            v = charref.sub(lambda m: unichr(int(m.groups()[0])), v)
            v = v.strip()
            v = v.replace('&lt;', '<').replace('&gt;', '>').replace('&apos;', "'").replace('&quot;', '"').replace('&amp;', '&')
            return v
        attrs = [(k.lower(), clean_attr(v)) for k, v in attrs]
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        return attrs
        
    def do_base(self, attrs):
        d = dict(self.normalize_attrs(attrs))
        if 'href' not in d:
            return
        self.base_url = d['href']
    
    def error(self, *a, **kw): pass # We're not picky, we are Devo

        
class LinkParser(BaseParser):
    def do_link(self, attrs):
        d = dict(self.normalize_attrs(attrs))
        if 'rel' not in d: 
            return
        rels = d['rel'].split()
        if 'alternate' not in rels:
            return
        if d.get('type') not in FEED_TYPES:
            return
        if 'href' not in d:
            return
        
        self.links.append(urlparse.urljoin(self.base_url, d['href']))


def get_links(data, base_url):
    """
    Return a list of the feed links found
    """
    p = LinkParser(base_url)
    p.feed(data)
    return p.links

def get_link(data, base_url):
    """
    Return the first feed link found, otherwise return None
    """
    links = get_links(data, base_url)
    if links:        
        return links[0]    


# def sniff(data): 
#     data = data.lower()
#     if data.count('<html'): return 0
#     return data.count('<rss') + data.count('<rdf') + data.count('<feed')

 
