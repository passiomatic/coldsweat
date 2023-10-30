from datetime import datetime
import itertools
import flask
import flask_login
from flask import current_app as app
from peewee import IntegrityError
from playhouse.flask_utils import get_object_or_404
from requests.exceptions import RequestException
from ..models import (User, Feed, Group, Subscription, Entry, Read, Saved)
import coldsweat.models as models
import coldsweat.feed as feed
import coldsweat.fetcher as fetcher
import coldsweat.markup as markup
from . import bp
from . import queries
import coldsweat.utilities as utilities

ENTRIES_PER_PAGE = 50
FEEDS_PER_PAGE = 50
GROUPS_PER_PAGE = 30


@bp.route('/')
@flask_login.login_required
def index():
    return entry_list()

# @bp.route('/nav')
# @flask_login.login_required
# def nav():
#     # These three ids allow to restore the UI panels
#     group_id = flask.request.args.get('group_id',  0, type=int)
#     feed_id = flask.request.args.get('feed_id', 0, type=int)
#     # @@TODO
#     #entry_id = flask.request.args.get('entry_id', 0, type=int)

#     user = flask_login.current_user.db_user

#     groups_feeds = itertools.groupby(queries.get_groups_and_feeds(user), lambda q: (q.group_id, q.group_title, q.group_read_count))

#     total_unread_count = queries.get_total_unread_count(user)

#     view_variables = {
#         'feed_id': feed_id,
#         'group_id': group_id,
#         'is_xhr': flask.request.args.get('xhr', 0, type=int),
#         'groups_feeds': groups_feeds,
#         'total_unread_count': total_unread_count
#     }

#     return flask.render_template('main/_nav.html', **view_variables)

@bp.route('/entries')
@flask_login.login_required
def entry_list():
    offset = flask.request.args.get('offset', 0, type=int)
    # These three ids allow to restore the UI panels
    group_id = flask.request.args.get('group_id',  0, type=int)
    feed_id = flask.request.args.get('feed_id', 0, type=int)
    # @@TODO
    #entry_id = flask.request.args.get('entry_id', 0, type=int)

    user = flask_login.current_user.db_user

    r = Entry.select(Entry.id).join(Read).where((Read.user ==
                                                 user)).objects()
    s = Entry.select(Entry.id).join(Saved).where((Saved.user ==
                                                  user)).objects()
    read_ids = dict((i.id, None) for i in r)
    saved_ids = dict((i.id, None) for i in s)

    groups_feeds = itertools.groupby(queries.get_groups_and_feeds(user), lambda q: (q.group_id, q.group_title, q.group_read_count))

    page_title = 'All Articles'
    if group_id:
        query = queries.get_group_entries(user, group_id)
        group = Group.get_or_none(Group.id==group_id)
        page_title = group.title if group else ''
    elif feed_id: 
        query = queries.get_feed_entries(user, feed_id)
        feed = Feed.get_or_none(Feed.id==feed_id)        
        page_title = feed.title if feed else ''
    else:
        query = queries.get_all_entries(user)

    # Check URL or cookie value for current filter
    filter = flask.request.args.get('filter') or flask.request.cookies.get('filter')
    if filter == 'saved':
        query = query.where(Entry.id << Saved.select(Saved.entry).where(Saved.user == user))
    elif filter == 'unread':
        query = query.where(~(Entry.id << Read.select(Read.entry).where(Read.user == user)))
    else:
        filter = 'archive'

    total_unread_count = queries.get_total_unread_count(user)

    view_variables = {
        'entries': query.order_by(
            Entry.published_on.desc()
        ).offset(offset).limit(ENTRIES_PER_PAGE),
        'read_ids': read_ids,
        'saved_ids': saved_ids,
        'feed_id': feed_id,
        'group_id': group_id,
        'count': query.count(),
        'offset': offset + ENTRIES_PER_PAGE,
        'prev_date': flask.request.args.get('prev_date', None),
        'is_xhr': flask.request.args.get('xhr', 0, type=int),
        'filter': filter,
        'page_title': page_title,
        'groups_feeds': groups_feeds,
        'total_unread_count': total_unread_count
    }
    if offset:
        return flask.render_template("main/entries-more.html", **view_variables)

    response = flask.make_response(flask.render_template("main/entries.html", **view_variables))
    # Remember last used filter across requests
    response.set_cookie('filter', filter)
    return response

# @bp.route('/entries/<int:entry_id>')
# @flask_login.login_required
# def entry_detail(entry_id):
#     entry = get_object_or_404(Entry, (Entry.id == entry_id))

#     user = flask_login.current_user.db_user

#     feed.mark_entry(user, entry, 'read')
#     view_variables = {
#         'entry': entry,
#         'saved_ids': [],
#         'read_ids': [],
#         'is_xhr': flask.request.args.get('xhr', 0, type=int),
#     }

#     return flask.render_template('main/_entry.html', **view_variables)

@bp.route('/entries/<int:entry_id>')
@flask_login.login_required
def entry_detail(entry_id):
    # These three ids allow to restore the UI panels
    group_id = flask.request.args.get('group_id',  0, type=int)
    feed_id = flask.request.args.get('feed_id', 0, type=int)
    user = flask_login.current_user.db_user

    # We need to rebuild nav and article view
    groups_feeds = itertools.groupby(queries.get_groups_and_feeds(user), lambda q: (q.group_id, q.group_title, q.group_read_count))
    total_unread_count = queries.get_total_unread_count(user)
    entry = get_object_or_404(Entry, (Entry.id == entry_id))

    feed.mark_entry(user, entry, 'read')
    view_variables = {
        'feed_id': feed_id,
        'group_id': group_id,
        'entry': entry,
        'saved_ids': [], # @@TODO
        'read_ids': [], # @@TODO
        'groups_feeds': groups_feeds,
        'total_unread_count': total_unread_count,
        'is_xhr': flask.request.args.get('xhr', 0, type=int),
    }

    return flask.render_template('main/_entry.html', **view_variables)

@bp.route('/entries/<int:entry_id>', methods=["POST"])
@flask_login.login_required
def entry_mark(entry_id):
    try:
        status = flask.request.form['as']
    except KeyError:
        flask.abort(400, 'Missing parameter as=read|unread|saved|unsaved')

    user = flask_login.current_user.db_user
    entry = get_object_or_404(Entry, (Entry.id == entry_id))

    if 'mark' in flask.request.form:
        feed.mark_entry(user, entry, status)    

    return ('', 200)


# @bp.route('/feeds')
# @flask_login.login_required
# def feed_list():
#     '''
#     Show subscribed feeds
#     '''
#     offset, group_id, feed_id, filter_class, panel_title, page_title = \
#         0, 0, 0, 'feeds', 'Feeds', 'Feeds'

#     offset = flask.request.args.get('offset', 0, type=int)
#     user = flask_login.current_user.db_user
#     max_errors = 100
#     groups = feed.get_groups(user)
#     count, query = feed.get_feeds(user, Feed.id).count(), feed.get_feeds(user)
#     feeds = query.order_by(Feed.title).offset(offset).limit(FEEDS_PER_PAGE)
#     offset += FEEDS_PER_PAGE
#     is_xhr = flask.request.args.get('xhr', 0, type=int)

#     return flask.render_template('main/feeds.html', **locals())


@bp.route('/groups')
@flask_login.login_required
def group_list():
    '''
    Show feed groups
    '''
    offset, group_id, filter_class, panel_title, page_title = \
        0, 0, 'groups', 'Groups', 'Groups'

    offset = flask.request.args.get('offset', 0, type=int)
    user = flask_login.current_user.db_user
    count, query = feed.get_groups(user).count(), feed.get_groups(user)
    groups = query.offset(offset).limit(GROUPS_PER_PAGE)
    offset += GROUPS_PER_PAGE
    is_xhr = flask.request.args.get('xhr', 0, type=int)

    return flask.render_template('main/groups.html', **locals())


@bp.route('/entries/mark', methods=['GET', 'POST'])
@flask_login.login_required
def entry_list_mark():
    '''
    Mark feed|group|all entries as read
    '''
    feed_id = flask.request.args.get('feed_id', 0, type=int)
    group_id = flask.request.args.get('group_id', 0, type=int)

    if flask.request.method == 'GET':
        now = datetime.utcnow()
        if feed_id:
            template = 'main/_entries_mark_feed_read.html'
        elif group_id:
            template = 'main/_entries_mark_group_read.html'
        else:
            template = 'main/_entries_mark_all_read.html'
        return flask.render_template(template, feed_id=feed_id, group_id=group_id, now=now)

    # Handle postback
    try:
        before = datetime.utcfromtimestamp(flask.request.form.get('before', type=int))
    except (KeyError, ValueError):
        flask.abort(400, 'Missing parameter before=time')

    user = flask_login.current_user.db_user

    if feed_id:
        try:
            feed = Feed.get((Feed.id == feed_id))
        except Feed.DoesNotExist:
            flask.abort(404, f'No such feed {feed_id}')

        q = (Entry.select(Entry)
             .join(Feed)
             .join(Subscription)
             .where((Subscription.user == user) &
                    # Exclude entries already marked as read
                    ~(Entry.id << Read.select(Read.entry).where(
                        Read.user == user)) &
                    # Filter by current feed
                    (Entry.feed == feed) &
                    # Exclude entries fetched after the page load
                    (Feed.last_checked_on < before)
                    ).distinct())
        flask.flash('Feed has been marked as read', category="info")
        redirect_url = flask.url_for('main.entry_list', feed=feed_id)
    elif group_id: 
        try:
            group = Group.get(Group.id == group_id)
        except Group.DoesNotExist:
            flask.abort(404, f'No such group {group_id}')

        q = (Entry.select(Entry)
             .join(Feed)
             .join(Subscription)
             .where((Subscription.user == user) & 
                    (Subscription.group == group) &
                    # Exclude entries already marked as read
                    ~(Entry.id << Read.select(
                        Read.entry).where(Read.user == user)) &
                    # Exclude entries fetched after the page load
                    (Entry.published_on < before)
                    ).distinct())
        flask.flash(f'All {group.title} entries have been marked as read', category="info")
        redirect_url = flask.url_for('main.entry_list', unread='')        
    else:
        q = Entry.select(Entry).join(Feed).join(Subscription).where(
            (Subscription.user == user) &
            # Exclude entries already marked as read
            ~(Entry.id << Read.select(Read.entry).where(
                Read.user == user)) &
            # Exclude entries fetched after the page load
            (Feed.last_checked_on < before)
        ).distinct()
        flask.flash('All entries have been marked as read', category="info")
        redirect_url = flask.url_for('main.entry_list', unread='')

    #  @@TODO: Use insert_many()
    with models.db_wrapper.database.transaction():
        for entry in q:
            try:
                Read.create(user=user, entry=entry)
            except IntegrityError:
                app.logger.debug(
                    'entry %d already marked as read, ignored' % entry.id)
                continue

    return _render_script('main/_dialog_done.js', location=redirect_url)


@bp.route('/groups/edit', methods=['GET', 'POST'])
@flask_login.login_required
def group_edit():
    group_id = flask.request.args.get('group_id', 0, type=int)

    try:
        group = Group.get(Group.id == group_id)
    except Group.DoesNotExist:
        flask.abort(404, 'No such group %s' % group_id)

    user = flask_login.current_user.db_user

    if flask.request.method == 'GET':
        return flask.render_template('main/_group_edit.html', group=group)

    # Handle postback
    title = flask.request.form.get('title', '').strip()
    color = flask.request.form.get('color', '')
    if not title:
        flask.flash('Error, group title cannot be empty.', category="error")
        return flask.render_template('main/_group_edit.html', group=group)
    group.title = title
    group.color = color
    group.save()
    flask.flash('Changes have been saved.')
    return _render_script('main/_group_edit_done.js', group=group)


@bp.route('/feeds/edit', methods=['GET', 'POST'])
@flask_login.login_required
def feed_edit():
    feed_id = flask.request.args.get('feed_id', 0, type=int)

    try:
        feed = Feed.get(Feed.id == feed_id)
    except Feed.DoesNotExist:
        flask.abort(404, 'No such feed %s' % feed_id)

    user = flask_login.current_user.db_user

    # Collect editable fields
    title = feed.title

    q = Subscription.select(
        Subscription, Group).join(Group).where(
        (Subscription.user == user
         ) & (Subscription.feed == feed))
    groups = [s.group for s in q]

    if flask.request.method == 'GET':
        # @@TODO remove locals()
        return flask.render_template('main/_feed_edit.html', **locals())

    # Handle postback
    title = flask.request.form.get('title', '').strip()
    enabled = flask.request.form.get('enabled') == "1"
    if not title:
        flask.flash('Error, feed title cannot be empty.', category="error")
        # @@TODO remove locals()
        return flask.render_template('main/_feed_edit.html', **locals())
    feed.title = title
    feed.enabled = enabled
    feed.save()
    flask.flash('Changes have been saved.')
    #flask.flash('Feed <i>%s</i> is now enabled.' % feed.title, category="info")
    return _render_script('main/_feed_edit_done.js', feed=feed)


@bp.route('/feeds/add/1', methods=['GET', 'POST'])
@flask_login.login_required
def feed_add_1():
    groups = feed.get_groups(flask_login.current_user.db_user)
    is_xhr = flask.request.args.get('xhr', 0, type=int)

    # Values could be passed via a GET (bookmarklet) or POST
    title = flask.request.values.get('title', '').strip()
    self_link = flask.request.values.get('self_link', '').strip()

    # Handle GET

    if flask.request.method == 'GET':
        return flask.render_template('main/_feed_add_wizard_1.html', **locals())

    # Handle POST

    group_id = flask.request.form.get('group', 0, type=int)

    # Assume HTTP if URL is passed w/out scheme
    self_link = self_link if self_link.startswith('http') else f'http://{self_link}'

    if not utilities.validate_url(self_link):
        flask.flash("Error, specify a valid web address", category="error")
        return flask.render_template('main/_feed_add_wizard_1.html', **locals())

    try:
        response = fetcher.fetch_url(self_link)
    except RequestException:
        flask.flash("Error, feed address is not correct or remote host is unreachable.", category="error")
        return flask.render_template('main/_feed_add_wizard_1.html', **locals())    
    if not markup.sniff_feed(response.text):
        links = markup.find_feed_links(response.text, base_url=self_link)
        return flask.render_template('main/_feed_add_wizard_2.html', **locals())

    # It's a feed

    feed_ = feed.add_feed_from_url(self_link, fetch_data=False)
    app.logger.debug("Starting fetcher for just subscribed feed")
    fetcher.Fetcher(feed_).update_feed_with_data(response.text)

    return _add_subscription(feed_, group_id)

@bp.route('/feeds/add/2', methods=['POST'])
@flask_login.login_required
def feed_add_2():

    self_link = flask.request.form.get('self_link', '')
    group_id = flask.request.form.get('group', 0, type=int)

# @@TODO: handle multiple feed subscription
#         urls = self.request.POST.getall('feeds')
#         for url in urls:
#             pass
# @@TODO: validate feed
#         try:
#             response = fetch_url(self_link)
#         except RequestException, exc:
#             form_message = (u'ERROR Error, feed address is incorrect or '
#                              'host is unreachable.')
#             return self.respond_with_template('_feed_add_wizard_1.html',
#                                               locals())

    feed_ = feed.add_feed_from_url(self_link, fetch_data=True)
    return _add_subscription(feed_, group_id)


@bp.route('/feeds/remove', methods=['GET', 'POST'])
@flask_login.login_required
def feed_remove():
    feed_id = flask.request.args.get('feed', 0, type=int)

    user = flask_login.current_user.db_user

    try:
        feed = Feed.get(Feed.id == feed_id)
    except Feed.DoesNotExist:
        flask.abort(404, 'No such feed %s' % feed_id)

    if flask.request.method == 'GET':
        return _render_modal(flask.url_for('main.feed_remove', feed=feed.id),
                             title='Remove <i>%s</i> from your subscriptions?'
                             % feed.title, button='Remove')

    # Handle postback
    Subscription.delete().where(
        (Subscription.user == user
         ) & (Subscription.feed == feed)).execute()
    flask.flash(
        f'You are no longer subscribed to <i>{feed.title}</i>.', category="info")

    return flask.redirect(flask.url_for('main.feed_list'))


@bp.route('/profile', methods=['GET', 'POST'])
@flask_login.login_required
def profile():

    user = flask_login.current_user.db_user

    if flask.request.method == 'POST':

        new_email = flask.request.form.get('email', '')
        new_display_name = flask.request.form.get('display_name', '')

        user.email = new_email
        user.display_name = new_display_name
        user.save()
        return _render_script('main/_dialog_done.js', location=flask.url_for("main.index"))

    return flask.render_template('main/_user_edit.html', user=user)


@bp.route('/export')
@flask_login.login_required
def export():
    user = flask_login.current_user.db_user
    groups_feeds = itertools.groupby(queries.get_groups_and_feeds(user), lambda q: q.group_title)

    template =  flask.render_template('main/export.xml', timestamp=datetime.utcnow(), groups_feeds=groups_feeds)
    r = flask.make_response(template)
    r.headers["Content-Type"] = "application/xml"
    return r


@bp.route('/cheatsheet')
def cheatsheet():
    return flask.render_template('main/_cheatsheet.html', **locals())


@bp.route('/log')
@flask_login.login_required
def fetch_log():
    log = queries.get_fetch_log()
    return flask.render_template('main/log.html', log=log)


def _add_subscription(feed_, group_id):
    if group_id:
        group = Group.get(Group.id == group_id)
    else:
        group = Group.get(Group.title == Group.DEFAULT_GROUP)

    subscription = feed.add_subscription(flask_login.current_user.db_user, feed_, group)
    if subscription:
        flask.flash(f"Feed has been added to <i>{group.title}</i> group", category="info")
    else:
        flask.flash(f"Feed is already in <i>{group.title}</i> group'", category="info")
    return _render_script('main/_feed_add_wizard_done.js', feed=feed_)


def _render_script(filename, **kwargs):
    template = flask.render_template(filename, **kwargs)
    r = flask.make_response(template)
    r.headers["Content-Type"] = "text/javascript"
    return r  


def _render_modal(url, title='', body='', button='Close', params=None):
    namespace = {
        'url': url,
        'title': title,
        'body': body,
        'params': params if params else [],
        'button_text': button
    }
    return flask.render_template('main/_modal_alert.html', **namespace)