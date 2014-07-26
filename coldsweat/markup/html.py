# -*- coding: utf-8 -*-
"""
Description: HTML parsers and manipulation functions

Copyright (c) 2013—2014 Andrea Peltrin
Portions are copyright (c) 2006 Aaron Swartz
Portions are copyright (c) 2002–4 Mark Pilgrim
"""


from HTMLParser import HTMLParser, HTMLParseError
import urlparse


HTML_RESERVED_CHARREFS = 38, 60, 62, 34
HTML_RESERVED_ENTITIES = 'amp', 'lt', 'gt', 'quot'

from ..filters import escape_html
from coldsweat import logger

def _normalize_attrs(attrs):
    '''
    Normalize certain attribute values
    '''
    return [(k, v.lower().strip() if k in ('rel', 'type') else v) for k, v in attrs]


class BaseParser(HTMLParser):
    
    #@@TODO: add all HTMl 5 elements
    recognized_elements = ['a', 'abbr', 'acronym', 'address', 'area', 'b', 'big',
      'blockquote', 'br', 'button', 'caption', 'center', 'cite', 'code', 'col',
      'colgroup', 'dd', 'del', 'dfn', 'dir', 'div', 'dl', 'dt', 'em', 'fieldset',
      'font', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input',
      'ins', 'kbd', 'label', 'legend', 'li', 'map', 'menu', 'ol', 'optgroup',
      'option', 'p', 'pre', 'q', 's', 'samp', 'select', 'small', 'span', 'strike',
      'strong', 'sub', 'sup', 'title', 'table', 'tbody', 'td', 'textarea', 'tfoot', 'th',
      'thead', 'tr', 'tt', 'u', 'ul', 'var']
          

    def handle_starttag(self, tag, attrs):        
        if tag in self.recognized_elements:
            handler = getattr(self, 'start_%s' % tag, None)
            if handler:
                handler(attrs)
                return
                        
        self.unknown_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in self.recognized_elements:
            handler = getattr(self, 'end_%s' % tag, None)
            if handler:
                handler()
                return
        
        self.unknown_endtag(tag)

    def unknown_starttag(self, tag, attrs):
        pass

    def unknown_endtag(self, tag):
        pass


class BaseProcessor(BaseParser):
    '''
    Parse and partially reconstruct the input document     
    '''

    # HTML 5 only    
    void_elements = ['area', 'base', 'br', 'col', 'command', 'embed', 'hr', 
      'img', 'input', 'keygen', 'link', 'meta', 'param', 'source', 'track', 'wbr' ]
      
    def __init__(self, xhtml_mode=False):
        BaseParser.__init__(self)
        self.xhtml_mode = xhtml_mode

    #@@NOTE: reset is called implicitly by base class
        
    def reset(self):
        BaseParser.reset(self)
        self.pieces = []
        
    def output(self):
        '''
        Return processed HTML as a single string
        '''
        return ''.join(self.pieces)    
        
    def unknown_starttag(self, tag, attrs):
        # Called for each unhandled tag, where attrs is a list of (attr, value) tuples
        #   e.g. for <pre class="screen">, tag="pre", attrs=[("class", "screen")]
        #   The attr name will be translated to lower case, and quotes in the  
        #   value have been removed and character and entity references 
        #   have been replaced. Starting Python 2.6 all entity references from 
        #   htmlentitydefs are replaced in the attribute values                    
        s = "".join([' %s="%s"' % (key, escape_html(value)) for key, value in attrs])
        if self.xhtml_mode and (tag in self.void_elements):
            self.pieces.append("<%s%s />" % (tag, s))
        else:
            self.pieces.append("<%s%s>" % (tag, s))
        
    def unknown_endtag(self, tag):
        # Called for each unhandled end tag, e.g. for </pre>, tag will be "pre"
        #   Reconstruct the original end tag.
        if tag not in self.void_elements:
            self.pieces.append("</%s>" % tag)
            
    def handle_charref(self, ref):
        # Called for each character reference, e.g. for "&#160;", ref will be "160"
        #   Unescape the original character reference if not reserved
        if ref in HTML_RESERVED_CHARREFS: 
            self.pieces.append("&#%s;" % ref) 
        else:
            self.pieces.append(self.unescape("&#%s;" % ref))

    def handle_entityref(self, ref):
        # Called for each entity reference, e.g. for "&copy;", ref will be "copy"
        #   Unescape the original entity reference if not reserved
        if ref in HTML_RESERVED_ENTITIES:
            self.pieces.append("&%s;" % ref)             
        else:                        
            self.pieces.append(self.unescape("&%s;" % ref))

    def handle_data(self, text):
        # Called for each block of plain text, i.e. outside of any tag and
        #   not containing any character or entity references
        #   Store the original text verbatim
        self.pieces.append(text)

    # The following elements will be stripped by 
    #   the default implementation

    def handle_comment(self, text):
        pass # Strip comments

    def handle_pi(self, text):
        pass # Strip pi

    def handle_decl(self, text):
        pass # Strip doctype declaration


class Stripper(BaseProcessor):

    def handle_starttag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        pass

    def handle_charref(self, ref):
        self.pieces.append(self.unescape("&#%s;" % ref))

    def handle_entityref(self, ref):
        self.pieces.append(self.unescape("&%s;" % ref))
                    
class FeedFinder(BaseParser):
    '''
    Find the feeds for a web page. Code derived from Feedfinder, 
      see: http://bit.ly/6dBgUf
    '''
    
    FEED_TYPES = [
        'application/rss+xml',
        'text/xml',
        'application/atom+xml',
        'application/x.atom+xml',
        'application/x-atom+xml'
    ]

    def __init__(self, base_url=''):
        BaseParser.__init__(self)
        self.links = []
        self.base_url= base_url

    
    def start_base(self, attrs):
        d = dict(attrs)
        if 'href' not in d:
            return
        self.base_url = d['href']
    
    def start_link(self, attrs):                
        d = dict(_normalize_attrs(attrs))
        if 'rel' not in d: 
            return
        rels = d['rel'].split()
        if 'alternate' not in rels:
            return
        if d.get('type') not in self.FEED_TYPES:
            return
        if 'href' not in d:
            return

        #@@TODO: check if it's relative URL before join
        self.links.append(urlparse.urljoin(self.base_url, d['href']))

class LinkFinder(BaseParser):
    '''
    Find all the anchor links for the given HTML content
    '''
    
    def __init__(self):
        BaseParser.__init__(self)
        self.links = []
        
    def start_a(self, attrs):            
        d = dict(_normalize_attrs(attrs))
        #@@NOTE: relative URL's should be resolved by Feedparser
        if 'href' in d:
            url = d['href']
            schema, netloc, path, query, fragment = urlparse.urlsplit(url)
            if schema in ['http','https']:          
                self.links.append(url)
                
class Scrubber(BaseProcessor):
    '''
    Remove annoying ads in entry images and links.
    '''

    def __init__(self, blacklist):
        BaseProcessor.__init__(self)
        self.blacklist, self.blacklisted = blacklist, 0   
            
    def start_a(self, attrs):
        d = dict(_normalize_attrs(attrs))
        if 'href' in d:
            if self.is_blacklisted(d['href']):
                #logger.debug('matched anchor with blacklisted href=%s' % d['href'])
                self.blacklisted += 1
                return
                
        # Proceed to default handling        
        self.unknown_starttag('a', attrs)

    def end_a(self):
        if self.blacklisted:
            self.blacklisted -= 1
        else:
            self.unknown_endtag('a')
                
    def start_img(self, attrs):
        d = dict(_normalize_attrs(attrs))
        if 'src' in d:        
            if self.is_blacklisted(d['src']):
                self.pieces.append(d['alt'] if 'alt' in d else '')
                #logger.debug('matched image with blacklisted src=%s' % d['src'])
                return

        # Proceed to default handling        
        self.unknown_starttag('img', attrs)
   

    def is_blacklisted(self, value):
        schema, netloc, path, params, query, fragment = urlparse.urlparse(value)

        for site in self.blacklist:
            if site in netloc:
                return True
        return False

class TitleFinder(BaseParser):
    
    def __init__(self):
        BaseParser.__init__(self)
        self.title, self.in_title  = '', 0

    def handle_data(self, text):
        if self.in_title:
            self.title += text
                        
    def start_title(self, attrs):     
        self.in_title += 1

    def end_title(self):            
        self.in_title -= 1


def _parse(parser, data):    
    try:
        parser.feed(data)    
    except HTMLParseError, exc:
        # Log exception and raise it again
        logger.debug('could not parse markup (%s)' % exc.msg)
        raise exc

# Discovery functions

def find_links(data):
    '''
    Return the <a>nchor links found for the page
    '''
    p = LinkFinder()
    _parse(p, data)
    return p.links
    
def find_feeds(data, base_url):
    '''
    Return the feed links found for the page
    '''
    p = FeedFinder(base_url)
    _parse(p, data)
    return p.links

def sniff_feed(data): 
    data = data.lower()
    if data.count('<html'):
        return False
    return any((data.count('<rss'), data.count('<rdf'), data.count('<feed')))
        
def find_title(data):
    '''
    Return the <title> of the page
    '''
    p = TitleFinder()
    _parse(p, data)
    return p.title.strip() # Remove extra spaces
    
# Misc.
        
def strip_html(data):
    '''
    Strip all HTML tags and convert all entities/charrefs, effectively 
      creating a plain text version of the input document
    '''
    p = Stripper()
    _parse(p, data)
    return p.output()

def scrub_html(data, blacklist):
    '''
    Remove blacklisted links and images from the input document
    '''
    p = Scrubber(blacklist)
    _parse(p, data)
    return p.output()



