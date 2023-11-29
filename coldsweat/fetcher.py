'''
The feed fetcher
'''

import urllib

from datetime import datetime
from peewee import chunked
import flask
from flask import current_app as app
import feedparser
import requests
from requests.exceptions import RequestException
import werkzeug.exceptions as exceptions
from werkzeug import http
from . import markup
from .models import (Entry, Feed, db_wrapper, FEED_GENERIC, FEED_MASTODON)
from .utilities import (datetime_as_epoch, 
                        tuple_as_datetime, 
                        scrub_url, 
                        truncate,
                        format_http_datetime,
                        make_sha1_hash,
                        make_data_uri,
                        make_nonce)
from . import __version__

__all__ = [
    'Fetcher',
    'fetch_url'
]

INSERT_CHUNK_SIZE = 100  # SQLite has a limit of total 999 max variables
FETCH_TIMEOUT = 10  # Seconds
MIN_FETCH_INTERVAL = 60*3  # Seconds
MAX_FETCH_ERRORS = 50
FETCH_ICONS_INTERVAL = 30  # Days
ENTRY_TAG_URI = 'tag:lab.passiomatic.com,2017:coldsweat:entry:%s'
USER_AGENT = ('Coldsweat/%d.%d.%d%s <https://lab.passiomatic.com/coldsweat/>' % __version__)


class Fetcher(object):
    '''
    Fetch a single given feed
    '''

    def __init__(self, feed):
        # Save timestamp for current fetch operation
        self.instant = datetime.utcnow()
        self.feed = feed

    def handle_500(self, response):
        '''
        Internal server error
        '''
        #self.feed.error_count += 1
        self.feed.last_status = response.status_code
        app.logger.warning(
            "%s has caused an error on server, skipped" % self.feed.self_link)
        raise exceptions.InternalServerError

    def handle_403(self, response):
        '''
        Forbidden
        '''
        self.feed.error_count += 1
        self.feed.last_status = response.status_code
        app.logger.warning("%s access was denied, skipped" % self.feed.self_link)
        raise exceptions.Forbidden

    def handle_404(self, response):
        '''
        Not Found
        '''
        self.feed.error_count += 1
        self.feed.last_status = response.status_code
        app.logger.warn("%s has been not found, skipped" % self.feed.self_link)
        raise exceptions.NotFound

    def handle_410(self, response):
        '''
        Gone
        '''
        self.feed.enabled = False
        self.feed.error_count += 1
        self.feed.last_statu = response.status_code
        app.logger.warning("%s is gone, disabled" % self.feed.self_link)
        self._synthesize_entry('Feed has been removed from the origin server.')
        raise exceptions.Gone

    def handle_304(self, response):
        '''
        Not modified
        '''
        app.logger.debug("%s hasn't been modified, skipped" % self.feed.self_link)
        self.feed.last_status = response.status_code

    def handle_301(self, response):
        '''
        Moved permanently
        '''
        self_link = response.url

        try:
            Feed.get(self_link=self_link)
        except Feed.DoesNotExist:
            self.feed.self_link = self_link
            self.feed.last_status = response.status_code
            app.logger.info(
                "%s has changed its location, updated to %s" % (
                    self.feed.self_link, self_link))
        else:
            self.feed.enabled = False
            self.feed.last_status = DuplicatedFeed.code
            self.feed.error_count += 1
            self._synthesize_entry('Feed has a duplicated web address.')
            app.logger.warning(
                "new %s location %s is duplicated, disabled" % (
                    self.feed.self_link, self_link))
            raise DuplicatedFeed

    def handle_200(self, response):
        '''
        OK plus redirects
        '''
        self.feed.etag = response.headers.get('ETag', '')
        # Save final status code discarding redirects
        self.feed.last_status = response.status_code
        self._parse_feed(response.text)
        self._fetch_icon()        

    handle_307 = handle_200   # Alias
    handle_303 = handle_200   # Alias
    handle_302 = handle_200   # Alias

    def update_feed(self):

        app.logger.debug("updating %s" % self.feed.self_link)

        # Check freshness
        for value in [self.feed.last_checked_on, self.feed.last_updated_on]:
            if not value:
                continue

            # No datetime.timedelta since we need to
            #   deal with large seconds values
            delta = datetime_as_epoch(self.instant) - datetime_as_epoch(value)
            # @@TODO Skip check while DEBUG env
            if delta < MIN_FETCH_INTERVAL:
                app.logger.debug(
                    "%s is below minimun fetch interval, skipped"
                    % self.feed.self_link)
                return

        try:
            response = fetch_url(self.feed.self_link,
                                 timeout=FETCH_TIMEOUT,
                                 etag=self.feed.etag,
                                 modified_since=self.feed.last_updated_on)
        except RequestException:
            # Record any network error as 'Service Unavailable'
            self.feed.last_status = exceptions.ServiceUnavailable.code
            #self.feed.error_count += 1
            app.logger.warning(
                "a network error occured while fetching %s, skipped"
                % self.feed.self_link)
            self.check_feed_health()
            self.feed.save()
            return

        self.feed.last_checked_on = self.instant

        # Check if we got a redirect first
        if response.history:
            status = response.history[0].status_code
        else:
            status = response.status_code

        try:
            handler = getattr(self, f'handle_{status}', None)
            if handler:
                app.logger.debug("got status %s from server" % status)
                handler(response)
            else:
                self.feed.last_status = status
                app.logger.warning(
                    "%s replied with unhandled status %d, aborted" % (
                        self.feed.self_link, status))
                return
        except exceptions.HTTPException:
            self.check_feed_health()
        finally:
            self.feed.save()

    def check_feed_health(self):
        if self.feed.error_count > MAX_FETCH_ERRORS:
            self._synthesize_entry(
                'Feed has accumulated too many errors (last was %s).'
                % self.feed.last_status)
            app.logger.warning(
                "%s has accomulated too many errors, disabled" % self.feed.self_link)
            self.feed.enabled = False

    def update_feed_with_data(self, data):
        self._parse_feed(data)
        self.feed.save()

    def _parse_feed(self, data):

        soup = feedparser.parse(data)
        # Got parsing error?
        if hasattr(soup, 'bozo') and soup.bozo:
            app.logger.debug(
                "%s caused a parser error (%s), tried to parse it anyway" % (
                    self.feed.self_link, soup.bozo_exception))

        self.feed.last_updated_on = get_feed_timestamp(soup.feed, self.instant)
        self.feed.alternate_link = get_feed_alternate_link(soup.feed)
        # Do not set title again if already set
        self.feed.title = self.feed.title or get_feed_title(soup.feed)
        self.feed.source = get_feed_generator(soup.feed)

        icon_url = get_feed_icon(soup.feed)
        if icon_url:
            self.feed.icon_url = icon_url        
        else:
            # Prefer alternate_link if available since self_link
            #   could point to Feed Burner or similar services            
            feed_hostname = urllib.parse.urlsplit(self.feed.alternate_link or self.feed.self_link).hostname
            self.feed.icon_url = f"https://icons.duckduckgo.com/ip3/{feed_hostname}.ico"
        
        feed_author = get_feed_author(soup.feed)

        new_entries = []
        for entry_dict in soup.entries:

            link = get_entry_link(entry_dict)
            guid = get_entry_guid(entry_dict, default=link)

            # If an entry doesn't have a link nor a GUID we
            #   cannot uniquely identify it
            if not guid:
                app.logger.warning(
                    'could not find GUID for entry from %s, skipped'
                    % self.feed.self_link)
                continue

            timestamp = get_entry_timestamp(entry_dict, default=self.instant)
            content_type, content = get_entry_content(entry_dict, ('text/plain', ''))
            thumbnail_url = get_entry_thumbnail_url(entry_dict)

            entry = {
                'feed_id': self.feed.id,
                'guid': guid,
                'link': link,
                'title': get_entry_title(entry_dict, default='Untitled'),
                'author': get_entry_author(entry_dict) or feed_author,
                'content': markup.parse_html(content),
                'content_type': content_type,
                'thumbnail_url': thumbnail_url,
                'published_on': timestamp
            }
            new_entries.append(entry)

        
        count = 0
        engine = db_wrapper.get_engine()
        with db_wrapper.database.atomic():
            for batch in chunked(new_entries, INSERT_CHUNK_SIZE):
                if engine in ['sqlite', 'postgres']:
                    count += (Entry.insert_many(batch).on_conflict(
                        conflict_target=[Entry.guid],
                        # Pass down these new values only for certain values
                        preserve=[Entry.title, Entry.author, Entry.content, Entry.content_type])
                        .as_rowcount()
                        .execute())
                else: 
                    # MySQL doesn't support conflict targets, see:
                    # https://stackoverflow.com/questions/74691515/python-peewee-using-excluded-to-resolve-conflict-resolution
                    count += (Entry.insert_many(batch).on_conflict(
                        # Pass down these new values only for certain fields
                        preserve=[Entry.title, Entry.author, Entry.content, Entry.content_type])
                        .as_rowcount()
                        .execute())
        
        app.logger.debug(f"added/updated {count} entries from {self.feed.self_link}")
        return count

    def _fetch_icon(self):

        if not self.feed.icon or not self.feed.icon_last_updated_on or \
           ((self.instant - self.feed.icon_last_updated_on).days > FETCH_ICONS_INTERVAL):
            self.feed.icon = self._favicon_fetcher(self.feed.icon_url)
            # If fetch is unsuccessful we'll retry to fetch after FETCH_ICONS_INTERVAL
            self.feed.icon_last_updated_on = self.instant

            app.logger.debug(f"fetched favicon at {self.feed.icon_url}")

    def _favicon_fetcher(self, url):
        '''
        Fetch a site favicon via service
        '''

        try:
            response = fetch_url(url)
        except RequestException as exc:
            app.logger.warning(
                "could not fetch favicon for %s (%s)" % (url, exc))
            # @@TODO: Endpoint should point to a default icon from static folder
            return (Feed.DEFAULT_ICON, url)

        return make_data_uri(
            response.headers['Content-Type'], response.content)

    def add_synthesized_entry(self, title, content_type, content):
        '''
        Create an HTML entry for this feed
        '''

        # Since we don't know the mechanism the feed used to build a GUID for
        # its entries synthesize a tag URI from the link and a random string. This makes
        # entries internally generated by Coldsweat reasonably globally unique
        guid = ENTRY_TAG_URI % make_sha1_hash(self.feed.self_link + make_nonce())

        entry = Entry(
            feed=self.feed,
            guid=guid,
            title=title,
            author='Coldsweat',
            content=content,
            content_type=content_type,
            published_on=self.instant
        )
        entry.save()
        app.logger.debug("synthesized entry %s" % guid)
        return entry

    def _synthesize_entry(self, reason):
        title = 'This feed has been disabled'
        content = flask.render_template('main/_entry_feed_disabled.html', reason=reason)
        return self.add_synthesized_entry(title, 'text/html', content)


def fetch_url(url, timeout=10, etag=None, modified_since=None):
    '''
    Fecth a given URL optionally issuing a 'Conditional GET' request
    '''

    request_headers = {
        'User-Agent': USER_AGENT
    }

    # Conditional GET headers
    if etag and modified_since:
        app.logger.debug(
            "fetching %s with a conditional GET (%s %s)" %
            (url, etag, format_http_datetime(modified_since)))
        request_headers['If-None-Match'] = etag
        request_headers['If-Modified-Since'] = format_http_datetime(
            modified_since)
    try:
        response = requests.get(url, timeout=timeout, headers=request_headers)
    except RequestException as exc:
        app.logger.debug(
            "tried to fetch %s but got %s" % (url, exc.__class__.__name__))
        raise exc
    return response


# ------------------------------------------------------
# Helpers
# ------------------------------------------------------

IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif']


def get_feed_generator(feed_dict):
    value = feed_dict.get('generator', '')
    if 'Mastodon' in value:
        return FEED_MASTODON
    return FEED_GENERIC


def get_feed_timestamp(feed_dict, default):
    for header in ['published_parsed', 'updated_parsed']:
        value = feed_dict.get(header, None)
        if value:
            # Fix future dates if necessary
            return min(tuple_as_datetime(value), default)
    app.logger.debug(u'no feed timestamp found, using default')
    return default


def get_feed_author(feed_dict):
    if 'name' in feed_dict.get('author_detail', []):
        return feed_dict.author_detail.name
    return ''


def get_feed_alternate_link(feed_dict):
    return feed_dict.get('link', '')


def get_feed_title(feed_dict):
    if 'title' in feed_dict:
        return truncate(markup.strip_html(feed_dict.title),
                        Feed.MAX_TITLE_LENGTH)
    return ''

def get_feed_icon(feed_dict):
    try:
        atom_icon = feed_dict['icon']
    except KeyError:
        atom_icon = ''

    try:
        rss_icon = feed_dict['image']['href']
        rss_icon_width = feed_dict['image']['width']
        rss_icon_height = feed_dict['image']['height']
    except KeyError:
        rss_icon = ''
        rss_icon_width = 0
        rss_icon_height = 0       

    # Check if square 
    if rss_icon and rss_icon_width and rss_icon_height and (rss_icon_width == rss_icon_height):
        return rss_icon
    
    return atom_icon

def get_entry_guid(entry_dict, default):
    """
    Get a useful GUID from a feed entry
    """
    if 'id' in entry_dict:
        return entry_dict.id or default
    else:
        return default


def get_entry_timestamp(entry_dict, default):
    """
    Select the best timestamp for an entry
    """
    for header in ['published_parsed', 'created_parsed', 'updated_parsed']:
        value = entry_dict.get(header, None)
        if value:
            # Fix future dates
            return min(tuple_as_datetime(value), default)
    app.logger.debug(u'no entry timestamp found, using default')
    return default


def get_entry_title(entry_dict, default):
    if 'title' in entry_dict:
        return truncate(markup.strip_html(entry_dict.title),
                        Entry.MAX_TITLE_LENGTH)
    return default


def get_entry_source(entry_dict):
    #  d = self.entry_dict.get('source')
    #  d['link']
    return ''


def get_entry_content(entry_dict, default):
    """
    Select the best content from an entry
    """
    candidates = entry_dict.get('content', [])
    if 'summary_detail' in entry_dict:
        candidates.append(entry_dict.summary_detail)
    for c in candidates:
        # Match text/html, application/xhtml+xml
        if 'html' in c.type:
            return c.type, c.value
    # Return first result, regardless of MIME type
    if candidates:
        return candidates[0].type, candidates[0].value

    app.logger.debug(u'no entry content found, using default')
    return default


def get_entry_thumbnail_url(entry_dict):
    #See https://www.rssboard.org/media-rss
    if 'media_content' in entry_dict:
        media_content = entry_dict['media_content'][0]
        try:
            image_type = media_content['type']
        except KeyError:
            image_type = None
        if image_type in IMAGE_TYPES:
            try:
                return media_content['url']
            except KeyError:
                pass
    if 'media_thumbnail' in entry_dict:
        # "... If multiple thumbnails are included, and time coding is not at play, 
        #  it is assumed that the images are in order of importance."
        media_thumbnail = entry_dict['media_thumbnail'][0]
        return media_thumbnail['url']
    return ''


def get_entry_link(entry_dict):
    # Special case for FeedBurner entries
    # https://stackoverflow.com/questions/25760622/difference-between-origlink-and-link-in-rss-feedback-xml-file
    if 'feedburner_origlink' in entry_dict:
        return scrub_url(entry_dict.feedburner_origlink)
    if 'link' in entry_dict:
        return scrub_url(entry_dict.link)
    return ''


def get_entry_author(entry_dict):
    if 'name' in entry_dict.get('author_detail', []):
        return entry_dict.author_detail.name
    return ''


# ------------------------------------------------------
# Custom error codes 9xx & exceptions
# ------------------------------------------------------


class DuplicatedFeed(exceptions.HTTPException):
    code = 900
    description = 'Feed address matches another already present in the database'

# Update Werkzeug status codes map
http.HTTP_STATUS_CODES[DuplicatedFeed.code] = "Duplicated feed"
