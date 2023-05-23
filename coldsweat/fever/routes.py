import re
from collections import defaultdict
from datetime import datetime, timedelta
from peewee import fn, IntegrityError

import flask
from coldsweat.fever import bp

from flask import current_app as app
from coldsweat.utilities import Struct, datetime_as_epoch
import coldsweat.feed as feed
import coldsweat.models as models
from coldsweat.models import (
    User, Feed, Group, Entry, Read, Saved, Subscription)


RE_DIGITS = re.compile('[0-9]+')
RECENTLY_READ_DELTA = 600  # 10 minutes
API_VERSION = 3
COMMANDS = 'groups feeds items unread_item_ids saved_item_ids mark unread_recently_read favicons links'.split()


@bp.route('/', methods=['GET'])
def index_get():
    return flask.render_template("fever/index.html")


@bp.route('/', methods=['POST'])
def index_post():
    app.logger.debug('client from %s requested: %s' % (
        flask.request.remote_addr, flask.request.url))

    if 'api' not in flask.request.args:
        flask.abort(400)  # Bad request

    result = Struct({'api_version': API_VERSION, 'auth': 0})

    if 'api_key' in flask.request.form:
        api_key = flask.request.form['api_key']
        user = User.validate_api_key(api_key)
        if not user:
            app.logger.warn('unknown API key %s, unauthorized' % api_key)
            return flask.jsonify(result)
    else:
        app.logger.warn('missing API key, unauthorized')
        return flask.jsonify(result)

    # Authorized
    result.auth = 1

    # It looks like client *can* send multiple commands at time
    all_commands = globals()
    for name in COMMANDS:
        if name in flask.request.args:
            try:
                handler = all_commands[f'{name}_command']
            except KeyError:
                app.logger.debug('unrecognized command %s, skipped' % name)
                # @@TODO End with flask.abort(400) instead?
                continue
            handler(user, result)

    result.last_refreshed_on_time = get_last_refreshed_on_time()

    return flask.jsonify(result)

# ------------------------------------------------------
# Fever API commands
# ------------------------------------------------------


def groups_command(user, result):
    q = feed.get_groups(user)
    result.groups = [{
        'id': group.id,
        'title': group.title
    } for group in q]
    result.feeds_groups = get_feed_groups(user)


def feeds_command(user, result):
    q = feed.get_feeds(user)
    result.feeds = [{
        'id': feed.id,
        'favicon_id': feed.id,
        'title': feed.title,
        'url': feed.self_link,
        'site_url': feed.alternate_link,
        'is_spark': 0,  # Unsupported, always zero
        'last_updated_on_time': feed.last_updated_on_as_epoch
    } for feed in q]
    result.feeds_groups = get_feed_groups(user)


def unread_item_ids_command(user, result):
    q = feed.get_unread_entries(user, Entry.id).objects()
    ids = [r.id for r in q]
    result.unread_item_ids = ','.join(map(str, ids))


def saved_item_ids_command(user, result):
    q = feed.get_saved_entries(user, Entry.id).objects()
    ids = [r.id for r in q]
    result.saved_item_ids = ','.join(map(str, ids))


def favicons_command(_, result):
    q = Feed.select()
    result.favicons = [{
        'id': feed.id,
        'data': feed.icon_or_default
    } for feed in q]


def items_command(user, result):

    result.total_items = feed.get_all_entries(user, Entry.id).count()
    # From the API: "Use the since_id argument with the highest id
    #  of locally cached items to request 50 additional items.
    if 'since_id' in flask.request.args:
        try:
            min_id = int(flask.request.args['since_id'])
            result.items = get_entries_min(user, min_id)
        except ValueError:
            pass

        return

    # From the API: "Use the max_id argument with the lowest id of locally
    #  cached items (or 0 initially) to request 50 previous items.
    if 'max_id' in flask.request.args:
        try:
            max_id = int(flask.request.args['max_id'])
            if max_id:
                result.items = get_entries_max(user, max_id)
        except ValueError:
            pass

        return

    # From the API: "Use the with_ids argument with a comma-separated list
    #  of item ids to request (a maximum of 50) specific items."
    if 'with_ids' in flask.request.args:
        with_ids = flask.request.args['with_ids']
        ids = [int(i) for i in with_ids.split(',') if RE_DIGITS.match(i)]
        result.items = get_entries(user, ids[:50])
        return

    # Unfiltered results
    result.items = get_entries(user)


def unread_recently_read_command(user, result):
    since = datetime.utcnow() - timedelta(seconds=RECENTLY_READ_DELTA)
    q = Read.delete().where((Read.user == user
                             ) & (Read.read_on > since))
    count = q.execute()
    app.logger.debug('%d entries marked as unread' % count)


def mark_command(user, result):

    try:
        mark, status, object_id = flask.request.form['mark'], \
            flask.request.form['as'], int(flask.request.form['id'])
    except (KeyError, ValueError) as ex:
        app.logger.debug('missing or invalid parameter (%s), ignored' % ex)
        return

    if mark == 'item':

        try:
            # Sanity check
            entry = Entry.get(Entry.id == object_id)
        except Entry.DoesNotExist:
            app.logger.debug('could not find entry %d, ignored' % object_id)
            return

        if status == 'read':
            try:
                Read.create(user=user, entry=entry)
            except IntegrityError:
                app.logger.debug(
                    'entry %d already marked as read, ignored' %
                    object_id)
                return
        # Strangely enough 'unread' is not mentioned in
        #  the Fever API, but Reeder app asks for it
        elif status == 'unread':
            count = Read.delete().where(
                (Read.user == user) & (Read.entry == entry)).execute()
            if not count:
                app.logger.debug(
                    'entry %d never marked as read, ignored' % object_id)
                return
        elif status == 'saved':
            try:
                Saved.create(user=user, entry=entry)
            except IntegrityError:
                app.logger.debug('entry %d already marked as saved, ignored'
                                 % object_id)
                return
        elif status == 'unsaved':
            count = Saved.delete().where((
                Saved.user == user) & (
                Saved.entry == entry)).execute()
            if not count:
                app.logger.debug(
                    u'entry %d never marked as saved, ignored' % object_id)
                return

        app.logger.debug('marked entry %d as %s' % (object_id, status))

    elif mark == 'feed' and status == 'read':

        try:
            # Sanity check
            feed = Feed.get(Feed.id == object_id)
        except Feed.DoesNotExist:
            app.logger.debug('could not find feed %d, ignored' % object_id)
            return

        # Unix timestamp of the the local client’s last items API request
        try:
            before = datetime.utcfromtimestamp(
                int(flask.request.form['before']))
        except (KeyError, ValueError) as ex:
            app.logger.debug(
                'missing or invalid parameter (%s), ignored' % ex)
            return

        q = Entry.select(Entry).join(Feed).join(Subscription).where(
            (Subscription.user == user) &
            (Subscription.feed == feed) &
            # Exclude entries already marked as read
            ~(Entry.id << Read.select(Read.entry).where(
                Read.user == user)) &
            # Exclude entries fetched after last sync
            (Entry.last_updated_on < before)
        ).distinct().objects()

        with models.database.transaction():
            for entry in q:
                try:
                    Read.create(user=user, entry=entry)
                except IntegrityError:
                    # Should not happen,
                    # due to the query above, log as warning
                    app.logger.warn(
                        'entry %d already marked as read, ignored'
                        % entry.id)
                    continue

        app.logger.debug('marked feed %d as %s' % (object_id, status))

    elif mark == 'group' and status == 'read':

        # Unix timestamp of the the local client’s 'last items' API request
        try:
            before = datetime.utcfromtimestamp(
                int(flask.request.form['before']))
        except (KeyError, ValueError) as ex:
            app.logger.debug(
                'missing or invalid parameter (%s), ignored' % ex)
            return

        # Mark all as read?
        if object_id == 0:
            q = Entry.select(Entry).join(Feed).join(Subscription).where(
                (Subscription.user == user) &
                # Exclude entries already marked as read
                ~(Entry.id << Read.select(Read.entry).where(
                    Read.user == user)) &
                # Exclude entries fetched after last sync
                (Entry.last_updated_on < before)
            ).distinct().objects()
        else:
            try:
                group = Group.get(Group.id == object_id)
            except Group.DoesNotExist:
                app.logger.debug(
                    'could not find group %d, ignored' % object_id)
                return

            q = Entry.select(Entry).join(Feed).join(
                Subscription).where(
                (Subscription.user == user) &
                (Subscription.group == group) &
                # Exclude entries already marked as read
                ~(Entry.id << Read.select(
                    Read.entry).where(Read.user == user)) &
                # Exclude entries fetched after last sync
                (Entry.last_updated_on < before)
            ).distinct().objects()

        with models.transaction():
            for entry in q:
                try:
                    Read.create(user=user, entry=entry)
                except IntegrityError:
                    # Should not happen thanks to the query above,
                    # log as warning
                    app.logger.warn(
                        'entry %d already marked as read, ignored'
                        % entry.id)
                    continue

        app.logger.debug('marked group %d as %s' % (object_id, status))

    else:
        app.logger.debug(
            'malformed mark command (mark %s (%s) as %s ), ignored' % (
                mark, object_id, status))


def links_command(_, result):
    # Hot links (unsupported)
    result.links = []


# ------------------------------------------------------
# Specific Fever queries
# ------------------------------------------------------


def get_feed_groups(user):
    q = Subscription.select(Subscription,
                            Feed, Group).join(Feed).switch(Subscription).join(
        Group).where(Subscription.user == user)
    groups = defaultdict(lambda: [])
    for s in q:
        groups[s.group.id].append(str(s.feed.id))
    result = []
    for g in groups:
        result.append({'group_id': g, 'feed_ids': ','.join(groups[g])})
    return result


def _get_entries(user, q):

    r = Entry.select(Entry.id).join(Read).where(Read.user == user).objects()
    s = Entry.select(Entry.id).join(Saved).where(Saved.user == user).objects()

    read_ids = dict((i.id, None) for i in r)
    saved_ids = dict((i.id, None) for i in s)

    result = []
    for entry in q:
        result.append({
            'id': entry.id,
            'feed_id': entry.feed.id,
            'title': entry.title,
            'author': entry.author,
            'html': entry.content,
            'url': entry.link,
            'is_saved': 1 if entry.id in saved_ids else 0,
            'is_read': 1 if entry.id in read_ids else 0,
            'created_on_time': entry.last_updated_on_as_epoch
        })
    return result


def get_entries(user, ids=None):

    if ids:
        where_clause = (Subscription.user == user) & (Entry.id << ids)
    else:
        where_clause = (Subscription.user == user)

    q = Entry.select(Entry,
                     Feed).join(Feed).join(
        Subscription).where(where_clause).distinct()
    return _get_entries(user, q)


def get_entries_min(user, min_id, bound=50):
    q = Entry.select(Entry, Feed).join(
        Feed).join(Subscription).where((Subscription.user == user)
                                       & (Entry.id > min_id
                                          )).distinct().limit(bound)
    return _get_entries(user, q)


def get_entries_max(user, max_id, bound=50):
    q = Entry.select(Entry,
                     Feed).join(Feed).join(Subscription).where(
        (Subscription.user == user) &
        (Entry.id < max_id)).distinct().limit(bound)
    return _get_entries(user, q)


def get_last_refreshed_on_time():
    '''
    Time of the most recently *refreshed* feed
    '''
    last_checked_on = Feed.select(fn.Max(Feed.last_checked_on)).scalar()
    if last_checked_on:
        return datetime_as_epoch(last_checked_on)

    # Fallback value
    return datetime_as_epoch(datetime.utcnow())
