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
from .models import (Entry, Feed, db_wrapper)
from .translators import EntryTranslator, FeedTranslator
from .utilities import (datetime_as_epoch,
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
        # Extract netloc
        _, self.netloc, _, _, _ = urllib.parse.urlsplit(feed.self_link)

        self.feed = feed

    def handle_500(self, response):
        '''
        Internal server error
        '''
        self.feed.error_count += 1
        self.feed.last_status = response.status_code
        app.logger.warning(
            "%s has caused an error on server, skipped" % self.netloc)
        raise exceptions.InternalServerError

    def handle_403(self, response):
        '''
        Forbidden
        '''
        self.feed.error_count += 1
        self.feed.last_status = response.status_code
        app.logger.warning("%s access was denied, skipped" % self.netloc)
        raise exceptions.Forbidden

    def handle_404(self, response):
        '''
        Not Found
        '''
        self.feed.error_count += 1
        self.feed.last_status = response.status_code
        app.logger.warn("%s has been not found, skipped" % self.netloc)
        raise exceptions.NotFound

    def handle_410(self, response):
        '''
        Gone
        '''
        self.feed.enabled = False
        self.feed.error_count += 1
        self.feed.last_statu = response.status_code
        app.logger.warning("%s is gone, disabled" % self.netloc)
        self._synthesize_entry('Feed has been removed from the origin server.')
        raise exceptions.Gone

    def handle_304(self, response):
        '''
        Not modified
        '''
        app.logger.debug("%s hasn't been modified, skipped" % self.netloc)
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
                    self.netloc, self_link))
        else:
            self.feed.enabled = False
            self.feed.last_status = DuplicatedFeed.code
            self.feed.error_count += 1
            self._synthesize_entry('Feed has a duplicated web address.')
            app.logger.warning(
                "new %s location %s is duplicated, disabled" % (
                    self.netloc, self_link))
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
    handle_302 = handle_200   # Alias

    def update_feed(self):

        app.logger.debug("updating %s" % self.netloc)

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
                    % self.netloc)
                return

        try:
            response = fetch_url(self.feed.self_link,
                                 timeout=FETCH_TIMEOUT,
                                 etag=self.feed.etag,
                                 modified_since=self.feed.last_updated_on)
        except RequestException:
            # Record any network error as 'Service Unavailable'
            self.feed.last_status = exceptions.ServiceUnavailable.code
            self.feed.error_count += 1
            app.logger.warning(
                "a network error occured while fetching %s, skipped"
                % self.netloc)
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
                        self.netloc, status))
                return
        except exceptions.HTTPException:
            self.check_feed_health()
        finally:
            self.feed.save()

    def check_feed_health(self):
        # @@TODO Increase error_count only with 4xx errors
        if self.feed.error_count > MAX_FETCH_ERRORS:
            self._synthesize_entry(
                'Feed has accumulated too many errors (last was %s).'
                % self.feed.last_status)
            app.logger.warning(
                "%s has accomulated too many errors, disabled" % self.netloc)
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
                    self.netloc, soup.bozo_exception))

        ft = FeedTranslator(soup.feed)

        self.feed.last_updated_on = ft.get_timestamp(self.instant)
        self.feed.alternate_link = ft.get_alternate_link()
        # Do not set title again if already set
        self.feed.title = self.feed.title or ft.get_title()

        feed_author = ft.get_author()

        new_entries = []
        for entry_dict in soup.entries:

            t = EntryTranslator(entry_dict)

            link = t.get_link()
            guid = t.get_guid(default=link)

            # If an entry doesn't have a link nor a GUID we
            #   cannot uniquely identify it
            if not guid:
                app.logger.warning(
                    'could not find GUID for entry from %s, skipped'
                    % self.netloc)
                continue

            timestamp = t.get_timestamp(default=self.instant)
            content_type, content = t.get_content(('text/plain', ''))

            entry = {
                'feed_id': self.feed.id,
                'guid': guid,
                'link': link,
                'title': t.get_title(default='Untitled'),
                'author': t.get_author() or feed_author,
                'content': content,
                'content_type': content_type,
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
                    # MySQL doesn't support conlict targets, see:
                    # https://stackoverflow.com/questions/74691515/python-peewee-using-excluded-to-resolve-conflict-resolution
                    count += (Entry.insert_many(batch).on_conflict(
                        # Pass down these new values only for certain values
                        preserve=[Entry.title, Entry.author, Entry.content, Entry.content_type])
                        .as_rowcount()
                        .execute())
        
        app.logger.debug(f"added/updated {count} entries from {self.netloc}")
        return count

    def _fetch_icon(self):

        if not self.feed.icon or not self.feed.icon_last_updated_on or \
           ((self.instant - self.feed.icon_last_updated_on).days > FETCH_ICONS_INTERVAL):
            # Prefer alternate_link if available since self_link could
            # point to Feed Burner or similar services
            self.feed.icon, self.feed.icon_url  = self._favicon_fetcher(
                self.feed.alternate_link or self.feed.self_link)
            self.feed.icon_last_updated_on = self.instant

            app.logger.debug(f"fetched favicon {self.feed.icon_url}")

    def _favicon_fetcher(self, url):
        '''
        Fetch a site favicon via service
        '''
        hostname = urllib.parse.urlsplit(url).hostname
        endpoint = f"https://icons.duckduckgo.com/ip3/{hostname}.ico"

        try:
            response = fetch_url(endpoint)
        except RequestException as exc:
            app.logger.warning(
                "could not fetch favicon for %s (%s)" % (url, exc))
            # @@TODO: Endpoint shoudl point to a default icon from static folder
            return (Feed.DEFAULT_ICON, endpoint)

        return (make_data_uri(
            response.headers['Content-Type'], response.content), endpoint)

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
# Custom error codes 9xx & exceptions
# ------------------------------------------------------


class DuplicatedFeed(exceptions.HTTPException):
    code = 900
    description = 'Feed address matches another already present in the database'

# Update Werkzeug status codes map
http.HTTP_STATUS_CODES[DuplicatedFeed.code] = "Duplicated feed"
