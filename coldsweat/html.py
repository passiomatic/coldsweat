# -*- coding: utf-8 -*-
"""
Description: HTML parsers and manipulation functions

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2006 Aaron Swartz
Portions are copyright (c) 2002–4 Mark Pilgrim
"""


from sgmllib import SGMLParser, charref
import urlparse
from coldsweat import log

class BaseParser(SGMLParser):

    def __init__(self, base_url):
        SGMLParser.__init__(self)
        self.base_url = base_url
        
    def normalize_attrs(self, attrs):
        def clean_attr(v):
            v = charref.sub(lambda m: unichr(int(m.groups()[0])), v)
            v = v.strip()
            v = v.replace('&lt;', '<').replace('&gt;', '>').replace('&apos;', "'").replace('&quot;', '"').replace('&amp;', '&')
            return v
        attrs = [(k.lower(), clean_attr(v)) for k, v in attrs]
        attrs = [(k, v.lower() if k in ('rel', 'type') else v) for k, v in attrs]
        return attrs
        
    def do_base(self, attrs):
        d = dict(self.normalize_attrs(attrs))
        if 'href' not in d:
            return
        self.base_url = d['href']
    
    def error(self, *a, **kw): pass # We're not picky, we are Devo

        
class LinkParser(BaseParser):
    """
    Find the feeds for a web page. Code derived from Feedfinder, 
    see: http://www.aaronsw.com/2002/feedfinder/
    """
    
    FEED_TYPES = [
        'application/rss+xml',
        'text/xml',
        'application/atom+xml',
        'application/x.atom+xml',
        'application/x-atom+xml'
    ]

    def __init__(self, base_url):
        BaseParser.__init__(self, base_url)
        self.links = []

    def do_link(self, attrs):
        d = dict(self.normalize_attrs(attrs))
        if 'rel' not in d: 
            return
        rels = d['rel'].split()
        if 'alternate' not in rels:
            return
        if d.get('type') not in self.FEED_TYPES:
            return
        if 'href' not in d:
            return
        
        self.links.append(urlparse.urljoin(self.base_url, d['href']))


def find_feed_links(data, base_url):
    """
    Return the feed links found for the page
    """
    p = LinkParser(base_url)
    p.feed(data)
    return p.links

def find_feed_link(data, base_url):
    """
    Return the first feed link found
    """
    links = find_feed_links(data, base_url)
    if links:        
        return links[0]    
    return None


# def sniff(data): 
#     data = data.lower()
#     if data.count('<html'): return 0
#     return data.count('<rss') + data.count('<rdf') + data.count('<feed')

 
 
class ScrubParser(BaseParser):
    """
    Remove annoying ads in entry images and links.
    """

    elements_no_end_tag = ['area', 'base', 'basefont', 'br', 'col', 'frame', 'hr',
      'img', 'input', 'isindex', 'link', 'meta', 'param']
      
    def __init__(self, blacklist):
        BaseParser.__init__(self, blacklist)
        self.blacklist = blacklist   
        self.pieces = []
        self.blacklisted = 0

    def reset(self):
        self.pieces = []
        BaseParser.reset(self)
        
    def unknown_starttag(self, tag, attrs):
        # called for each start tag
        # attrs is a list of (attr, value) tuples
        # e.g. for <pre class="screen">, tag="pre", attrs=[("class", "screen")]
        strattrs = "".join([' %s="%s"' % (key, value) for key, value in attrs])
        if tag in self.elements_no_end_tag:
            self.pieces.append("<%(tag)s%(strattrs)s />" % locals())
        else:
            self.pieces.append("<%(tag)s%(strattrs)s>" % locals())
        
    def unknown_endtag(self, tag):
        # called for each end tag, e.g. for </pre>, tag will be "pre"
        # Reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%(tag)s>" % locals())

    def handle_charref(self, ref):
        # called for each character reference, e.g. for "&#160;", ref will be "160"
        # Reconstruct the original character reference.
        self.pieces.append("&#%(ref)s;" % locals())

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for "&copy;", ref will be "copy"
        # Reconstruct the original entity reference.
        self.pieces.append("&%(ref)s;" % locals())

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        self.pieces.append(text)

#     def handle_comment(self, text):
#         # called for each HTML comment, e.g. <!-- insert Javascript code here -->
#         # Reconstruct the original comment.
#         self.pieces.append("<!--%(text)s-->" % locals())

#     def handle_pi(self, text):
#         # called for each processing instruction, e.g. <?instruction>
#         # Reconstruct original processing instruction.
#         self.pieces.append("<?%(text)s>" % locals())

#     def handle_decl(self, text):
#         # called for the DOCTYPE, if present, e.g.
#         # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
#         #     "http://www.w3.org/TR/html4/loose.dtd">
#         # Reconstruct original DOCTYPE
#         self.pieces.append("<!%(text)s>" % locals())

    def start_a(self, attrs):
        d = dict(self.normalize_attrs(attrs))
        if 'href' in d:
            if self.is_blacklisted(d['href']):
                log.debug('matched anchor with blacklisted href=%s' % d['href'])
                self.blacklisted += 1
                return
                
        self.unknown_starttag('a', attrs)


    def end_a(self):
        if self.blacklisted:
            self.blacklisted -= 1
        else:
            self.unknown_endtag('a')
                
    def start_img(self, attrs):
        d = dict(self.normalize_attrs(attrs))
        if 'src' in d:        
            if self.is_blacklisted(d['src']):
                self.pieces.append(d['alt'] if 'alt' in d else '')
                log.debug('matched image with blacklisted src=%s' % d['src'])
                return
        
        self.unknown_starttag('img', attrs)

    def output(self):
        """
        Return processed HTML as a single string
        """
        return "".join(self.pieces)        


    def is_blacklisted(self, value):
        schema, netloc, path, params, query, fragment = urlparse.urlparse(value)

        for site in self.blacklist:
            if site in netloc:
                return True
        return False


def scrub_entry(data, blacklist):
    """
    Return the content on an entry, scrubbed
    """
    p = ScrubParser(blacklist)
    p.feed(data)
    return p.output()


