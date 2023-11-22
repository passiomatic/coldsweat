'''
HTML parsers and manipulation functions
'''

from html.parser import HTMLParser
import urllib.parse as urlparse
from feedparser.sanitizer import _HTMLSanitizer
# from flask import current_app as app
import markupsafe

HTML_RESERVED_CHARREFS = 38, 60, 62, 34
HTML_RESERVED_ENTITIES = 'amp', 'lt', 'gt', 'quot'


# Allow iframe elements in FeedParser 
_HTMLSanitizer.acceptable_elements.add("iframe")

def _normalize_attrs(attrs):
    '''
    Normalize certain attribute values
    '''
    return [(k, v.lower().strip() if k in ('rel', 'type') else v)
            for k, v in attrs]


class BaseParser(HTMLParser):

    def handle_starttag(self, tag, attrs):
        handler = getattr(self, 'start_%s' % tag, None)
        if handler:
            handler(attrs)
        else:
            self.unknown_starttag(tag, attrs)

    def handle_endtag(self, tag):
        handler = getattr(self, 'end_%s' % tag, None)
        if handler:
            handler()
        else:
            self.unknown_endtag(tag)

    def unknown_starttag(self, tag, attrs):
        pass

    def unknown_endtag(self, tag):
        pass


DOMAIN_WHITELIST = set(["www.youtube.com", "www.youtube-nocookie.com", "player.vimeo.com"])

class BaseProcessor(BaseParser):
    '''
    Parse and partially reconstruct the input document
    '''

    # HTML 5 only
    void_elements = ['area', 'base', 'br', 'col', 'command', 'embed', 'hr',
                     'img', 'input', 'keygen', 'link', 'meta', 'param',
                     'source', 'track', 'wbr']

    def __init__(self, xhtml_mode=False):
        BaseParser.__init__(self)
        self.xhtml_mode = xhtml_mode

    def reset(self):
        # Reset is called implicitly by base class on init
        BaseParser.reset(self)
        self.found_iframe = 0
        self.pieces = []

    def get_output(self):
        '''
        Return processed HTML as a single string
        '''
        return ''.join(self.pieces)

    def start_iframe(self, attrs):
        d = dict(_normalize_attrs(attrs))
        if self.is_allowed(d['src']):
            # Reconstruct element
            self.found_iframe = 1
            self.unknown_starttag('iframe', attrs)
        else:
            self.found_iframe = -1

    def end_iframe(self):
        if self.found_iframe > 0:
            self.unknown_endtag('iframe')
        self.found_iframe = 0

    def is_allowed(self, url):
        schema, netloc, path, params, query, fragment \
            = urlparse.urlparse(url)

        return (netloc.lower() in DOMAIN_WHITELIST)

    def unknown_starttag(self, tag, attrs):
        # Called for each unhandled tag, where attrs is a list of
        # (attr, value) tuples
        #   e.g. for <pre class="screen">, tag="pre", attrs=[("class",
        #                                                     "screen")]
        #   The attr name will be translated to lower case, and quotes in the
        #   value have been removed and character and entity references
        #   have been replaced. Starting Python 2.6 all entity references from
        #   htmlentitydefs are replaced in the attribute values
        s = "".join([' %s="%s"' % (key, markupsafe.escape(value)) for key, value in
                     attrs])
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
        # Called for each character reference, e.g. for "&#160;", ref will be
        # "160"
        #   Unescape the original character reference if not reserved
        if ref in HTML_RESERVED_CHARREFS:
            self.pieces.append("&#%s;" % ref)
        else:
            self.pieces.append(self.unescape("&#%s;" % ref))

    def handle_entityref(self, ref):
        # Called for each entity reference, e.g. for "&copy;", ref will be
        # "copy"
        #   Unescape the original entity reference if not reserved
        if ref in HTML_RESERVED_ENTITIES:
            self.pieces.append("&%s;" % ref)
        else:
            self.pieces.append(self.unescape("&%s;" % ref))

    def handle_data(self, text):
        # Called for each block of plain text, i.e. outside of any tag and
        #   not containing any character or entity references
        #   Store the original text verbatim
        if self.found_iframe >= 0:
            self.pieces.append(text)
        else:
            self.pieces.append(f'<p><em>[Removed content: {text}]</em></p>')
        

    # The following elements will be stripped by
    #   the default implementation

    def handle_comment(self, text):
        pass  # Strip comments

    def handle_pi(self, text):
        pass  # Strip pi

    def handle_decl(self, text):
        pass  # Strip doctype declaration


class FeedLinkFinder(BaseParser):
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
        self.base_url = base_url

    def start_base(self, attrs):
        d = dict(attrs)
        if 'href' not in d:
            return
        # Override passed base URL
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

        url, title = urlparse.urljoin(
            self.base_url, d['href']), d['title'] if 'title' in d else u''
        self.links.append((url, title))


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
                # app.logger.debug(
                #     u'matched anchor with blacklisted href=%s' % d['href'])
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
                # app.logger.debug(
                #     u'matched image with blacklisted src=%s' % d['src'])
                return

        # Proceed to default handling
        self.unknown_starttag('img', attrs)

    def is_blacklisted(self, value):
        schema, netloc, path, params, query, fragment \
            = urlparse.urlparse(value)

        for site in self.blacklist:
            if site in netloc:
                return True
        return False


def _parse(parser, data):
    try:
        parser.feed(data)
    except AssertionError as exc:
        # Log exception and raise it again
        # app.logger.debug(u'could not parse markup (%s)' % exc.msg)
        raise exc

# Link discovery functions


def find_feed_links(data, base_url=''):
    '''
    Return the feed links found for the page
    '''
    p = FeedLinkFinder(base_url)
    _parse(p, data)
    return p.links


def sniff_feed(data):
    data = data.lower()
    if data.count('<html'):
        return False
    return any((data.count('<rss'), data.count('<rdf'), data.count('<feed')))

# Misc.


def strip_html(data):
    return markupsafe.Markup(data).striptags()


def parse_html(data):
    p = BaseProcessor()
    _parse(p, data)
    return p.get_output()


def scrub_html(data, blacklist):
    '''
    Remove blacklisted links and images from the input document
    '''
    p = Scrubber(blacklist)
    _parse(p, data)
    return p.get_output()
