'''
Shared feed logic functions
'''

import time
from xml.etree import ElementTree
from flask import current_app as app
from peewee import JOIN, fn, IntegrityError
from .models import (Entry, Feed, Group, Read, Saved, Subscription)
from .utilities import make_sha1_hash, scrub_url
from .fetcher import Fetcher


def add_subscription(user, feed, group):
    '''
    Associate a feed/group pair to current user
    '''
    try:
        subscription = Subscription.create(user=user,
                                           feed=feed,
                                           group=group)
    except IntegrityError:
        app.logger.debug(
            'user %s already has feed %s in subscriptions' % (
                user.email, feed.self_link))
        return None

    app.logger.debug(
        'subscribed user %s to feed %s' % (
            user.email, feed.self_link))
    return subscription


def remove_subscription(user, feed):
    '''
    Remove a feed subscription for current user
    '''
    Subscription.delete().where(
        (Subscription.user == user) & (
            Subscription.feed == feed)).execute()

# ------------------------------------------------------
# Entry queries
# ------------------------------------------------------


def mark_entry(user, entry, status):
    '''
    Mark an entry as read|unread|saved|unsaved for current user
    '''
    if status == 'read':
        try:
            Read.create(user=user, entry=entry)
        except IntegrityError:
            app.logger.debug('entry %s already marked as read, ignored' %
                             entry.id)
            return
    elif status == 'unread':
        count = Read.delete().where((Read.user == user) & (
            Read.entry == entry)).execute()
        if not count:
            app.logger.debug(
                'entry %s never marked as read, ignored' % entry.id)
            return
    elif status == 'saved':
        try:
            Saved.create(user=user, entry=entry)
        except IntegrityError:
            app.logger.debug('entry %s already saved, ignored' % entry.id)
            return
    elif status == 'unsaved':
        count = Saved.delete().where((
            Saved.user == user) & (
                Saved.entry == entry)).execute()
        if not count:
            app.logger.debug('entry %s never saved, ignored' % entry.id)
            return

    app.logger.debug('marked entry %s as %s' % (entry.id, status))


def get_unread_entries(user, *select):
    # @@TODO: include saved information
    q = _q(*select).where((Subscription.user == user) &
                          ~(Entry.id << Read.select(Read.entry).where(
                              Read.user == user))).distinct()
    return q


def get_saved_entries(user, *select):
    # @@TODO: include read information
    q = _q(*select).where((Subscription.user == user) &
                          (Entry.id << Saved.select(Saved.entry).where(
                              Saved.user == user))).distinct()
    return q


def get_all_entries(user, *select):
    # @@TODO: include read and saved information
    q = _q(*select).where(Subscription.user == user).distinct()
    return q


def get_group_entries(user, group, *select):
    # @@TODO: include read and saved information
    q = _q(*select).where(
        (Subscription.user == user) &
        (Subscription.group == group))
    return q


def get_feed_entries(user, feed, *select):
    # @@TODO: include read and saved informatio
    q = _q(*select).where(
        (Subscription.user == user) &
        (Subscription.feed == feed)).distinct()
    return q

# ------------------------------------------------------
# Feeds queries
# ------------------------------------------------------


def get_feeds(user, *select):
    select = select or [Feed, fn.Count(Entry.id).alias('entry_count')]
    q = Feed.select(*select).join(
        Entry, JOIN.LEFT_OUTER).switch(
        Feed).join(Subscription).where(
        Subscription.user == user).group_by(Feed)
    return q


def get_group_feeds(user, group):
    q = Feed.select().join(
        Subscription).where((
            Subscription.user == user) &
        (Subscription.group == group))
    return q

# ------------------------------------------------------
# Groups queries
# ------------------------------------------------------


def get_groups(user):
    q = Group.select().join(
        Subscription).where(
            Subscription.user == user).distinct().order_by(
                Group.title)
    return q


def _q(*select):
    select = select or (Entry, Feed)
    q = Entry.select(*select).join(Feed).join(Subscription)
    return q


# ------------------------------------------------------
# Adding/removing
# ------------------------------------------------------


def add_feed(feed, fetch_data=False):
    '''
    Save a new feed object to database
    '''
    feed.self_link = scrub_url(feed.self_link)

    try:
        previous_feed = Feed.get(self_link=feed.self_link)
        app.logger.debug(
            f'feed {feed.self_link} has been already added to database, skipped')
        return previous_feed
    except Feed.DoesNotExist:
        pass

    feed.save()

    if fetch_data:
        fetch_feeds([feed])
    return feed


def add_feed_from_url(self_link, fetch_data=False):
    '''
    Save a new feed object to database via its URL
    '''
    feed = Feed(self_link=self_link)
    return add_feed(feed, fetch_data)


# @@TODO: delete feed if there are no subscribers
def remove_feed(feed):
    pass


def add_feeds_from_opml(filename, fetch_data=False):
    '''
    Add feeds to database reading from a file containing OPML data.
    '''

    # Map OPML attr keys to Feed model
    feed_allowed_attribs = {
        'xmlUrl': 'self_link',
        'htmlUrl': 'alternate_link',
        'title': 'title',
        'text': 'title',  # Alias for title
    }

    # Map OPML attr keys to Group model
    group_allowed_attribs = {
        'title': 'title',
        'text': 'title',  # Alias for title
    }

    default_group = Group.get(Group.title == Group.DEFAULT_GROUP)

    feeds = []
    groups = [default_group]

    for event, element in ElementTree.iterparse(filename,
                                                events=('start', 'end')):
        if event == 'start':
            if (element.tag == 'outline') and (
                    'xmlUrl' not in element.attrib):
                # Entering a group
                group = Group()

                for k, v in element.attrib.items():
                    if k in group_allowed_attribs:
                        setattr(group, group_allowed_attribs[k], v)

                try:
                    group = Group.get(Group.title == group.title)
                except Group.DoesNotExist:
                    group.save()
                    app.logger.debug(
                        'added group %s to database' % group.title)

                groups.append(group)

        elif event == 'end':
            if (element.tag == 'outline') and ('xmlUrl' in element.attrib):

                # Leaving a feed
                feed = Feed()

                for k, v in element.attrib.items():
                    if k in feed_allowed_attribs:
                        setattr(feed, feed_allowed_attribs[k], v)

                feed = add_feed(feed, fetch_data)
                feeds.append((feed, groups[-1]))
            elif element.tag == 'outline':
                # Leaving a group
                groups.pop()
    return feeds

# ------------------------------------------------------
# Fetching
# ------------------------------------------------------


def fetch_feeds(feeds):
    """
    Fetch given feeds, possibly parallelizing requests
    """

    start = time.time()

    app.logger.debug("starting fetcher")

    # if config.fetcher.processes:
    #     from multiprocessing import Pool
    #     # Each worker has its own connection
    #     p = Pool(4, initializer=database.connect)
    #     p.map(feed_worker, feeds)
    #     # Exit the worker processes so their connections do not leak
    #     p.close()
    # else:
    # Just sequence requests in this process
    for feed in feeds:
        feed_worker(feed)

    app.logger.info("fetch completed: %d feeds checked in %.1fs" % (
        len(feeds), time.time() - start))


def fetch_all_feeds():
    """
    Fetch all enabled feeds with at least one subscription
    """

    feeds = (Feed.select()
        .join(Subscription)
        .where(Feed.enabled == True))

    if feeds.count() == 0:
        app.logger.info("no feeds found to fetch, halted")
        return

    fetch_feeds(feeds)


def feed_worker(feed):
    fetcher = Fetcher(feed)
    fetcher.update_feed()
