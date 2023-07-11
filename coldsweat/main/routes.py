from datetime import datetime
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
import coldsweat.utilities as utilities

ENTRIES_PER_PAGE = 30
FEEDS_PER_PAGE = 60
GROUPS_PER_PAGE = 30


@bp.route('/')
@flask_login.login_required
def index():
    return entry_list()


@bp.route('/entries')
@flask_login.login_required
def entry_list():
    '''
    Show entries filtered and possibly paginated by:
        unread, saved, group or feed
    '''
    offset = flask.request.args.get('offset', 0, type=int)
    query, view_variables = _make_view_variables(flask_login.current_user.db_user)

    view_variables.update({
        'entries': query.order_by(
            Entry.published_on.desc()
        ).offset(offset).limit(ENTRIES_PER_PAGE),
        'offset': offset + ENTRIES_PER_PAGE,
        'prev_date': flask.request.args.get('prev_date', None),
        'is_xhr': flask.request.args.get('xhr', 0, type=int)
    })

    return flask.render_template("main/entries.html", **view_variables)


@bp.route('/entries/<int:entry_id>')
@flask_login.login_required
def entry(entry_id):
    entry = get_object_or_404(Entry, (Entry.id == entry_id))

    user = flask_login.current_user.db_user

    feed.mark_entry(user, entry, 'read')
    query, view_variables = _make_view_variables(user)
    n = query.where(Entry.published_on < entry.published_on).order_by(
        Entry.published_on.desc()).limit(1)

    view_variables.update({
        'entry': entry,
        'page_title': entry.title,
        'next_entries': n,
        'count': 0  # Fake it
    })

    return flask.render_template('main/entry.html', **view_variables)

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


@bp.route('/feeds')
@flask_login.login_required
def feed_list():
    '''
    Show subscribed feeds
    '''
    offset, group_id, feed_id, filter_class, panel_title, page_title = \
        0, 0, 0, 'feeds', 'Feeds', 'Feeds'

    offset = flask.request.args.get('offset', 0, type=int)
    user = flask_login.current_user.db_user
    max_errors = 100
    groups = feed.get_groups(user)
    count, query = feed.get_feeds(user, Feed.id).count(), feed.get_feeds(user)
    feeds = query.order_by(Feed.title).offset(offset).limit(FEEDS_PER_PAGE)
    offset += FEEDS_PER_PAGE
    is_xhr = flask.request.args.get('xhr', 0, type=int)

    return flask.render_template('main/feeds.html', **locals())


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
    Mark feed|all entries as read
    '''
    feed_id = flask.request.args.get('feed', 0, type=int)

    if flask.request.method == 'GET':
        now = datetime.utcnow()
        return flask.render_template('main/_entries_mark_%s_read.html' % ('feed' if feed_id else 'all'), **locals())

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

        q = Entry.select(Entry).join(Feed).join(Subscription).where(
            (Subscription.user == user) &
            # Exclude entries already marked as read
            ~(Entry.id << Read.select(Read.entry).where(
                Read.user == user)) &
            # Filter by current feed
            (Entry.feed == feed) &
            # Exclude entries fetched after the page load
            (Feed.last_checked_on < before)
        ).distinct()
        flask.flash('Feed has been marked as read', category="info")
        redirect_url = flask.url_for('main.entry_list', feed=feed_id)
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

    return _render_script('main/_modal_done.js', location=redirect_url)


@bp.route('/feeds/edit', methods=['GET', 'POST'])
@flask_login.login_required
def feed_edit():
    feed_id = flask.request.args.get('feed', 0, type=int)

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
        return flask.render_template('main/_feed_edit.html', **locals())

    # Handle postback
    title = flask.request.form.get('title', '').strip()
    if not title:
        flask.flash('Error, feed title cannot be empty.', category="error")
        return flask.render_template('main/_feed_edit.html', **locals())
    feed.title = title
    feed.save()
    flask.flash('Changes have been saved.')
    return _render_script('main/_modal_done.js', location=flask.url_for("main.entry_list", feed=feed.id))


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
        flask.flash("Error, feed address is incorrect or remote host is unreachable.", category="error")
        return flask.render_template('main/_feed_add_wizard_1.html', **locals())    
    if not markup.sniff_feed(response.text):
        links = markup.find_feed_links(response.text, base_url=self_link)
        return flask.render_template('main/_feed_add_wizard_2.html', **locals())

    # It's a feed

    feed_ = feed.add_feed_from_url(self_link, fetch_data=False)
    #app.logger.debug("starting fetcher")
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


@bp.route('/feeds/enable', methods=['GET', 'POST'])
@flask_login.login_required
def feed_enable():

    feed_id = flask.request.args.get('feed', 0, type=int)

    #user = flask_login.current_user.db_user
    # @@TODO: Check if user is subscribed too?
    try:
        feed = Feed.get(Feed.id == feed_id)
    except Feed.DoesNotExist:
        flask.abort(404, 'No such feed %s' % feed_id)

    if flask.request.method == 'GET':
        return _render_modal(flask.url_for('main.feed_enable', feed=feed.id),
            title='Enable <i>%s</i> again?' % feed.title, 
            body='Coldsweat will attempt to update it again during the next fetch.', button='Enable')
            
    # Handle postback
    feed.enabled = True
    feed.error_count = 0
    feed.save()
    flask.flash('Feed <i>%s</i> is now enabled.' % feed.title, category="info")

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
        return _render_script('main/_modal_done.js', location=flask.url_for("main.index"))

    return flask.render_template('main/_user_edit.html', user=user)


@bp.route('/cheatsheet')
def cheatsheet():
    return flask.render_template('main/_cheatsheet.html', **locals())


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
    return _render_script('main/_modal_done.js', location=flask.url_for("main.entry_list", feed=feed_.id))


def _render_script(filename, location):
    template = flask.render_template(filename, location=location)
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


def _make_view_variables(user):

    count, group_id, feed_id, filter_name, \
        filter_class, panel_title, page_title = 0, 0, 0, '', '', '', ''

    groups = feed.get_groups(user)
    r = Entry.select(Entry.id).join(Read).where((Read.user ==
                                                 user)).objects()
    s = Entry.select(Entry.id).join(Saved).where((Saved.user ==
                                                  user)).objects()
    read_ids = dict((i.id, None) for i in r)
    saved_ids = dict((i.id, None) for i in s)

    filter = flask.request.args.get('filter', 'unread')
    if filter == 'saved':
        count = feed.get_saved_entries(user, Entry.id).count()
        q = feed.get_saved_entries(user)
        panel_title = 'Saved'
        filter_class = filter_name = 'saved'
        page_title = 'Saved'
    elif filter ==  'group':
        group_id = flask.request.args.get('id', type=int)
        group = Group.get(Group.id == group_id)
        count = feed.get_group_entries(user, group, Entry.id).count()
        q = feed.get_group_entries(user, group)
        panel_title = group.title
        filter_class = 'groups'  # The same when listing group
        filter_name = f'group={group_id}'
        page_title = group.title
    elif filter ==  'feed':
        feed_id = flask.request.args.get('id', type=int)
        feed_ = Feed.get(Feed.id == feed_id)
        count = feed.get_feed_entries(user, feed_, Feed.id).count()
        q = feed.get_feed_entries(user, feed_)
        panel_title = feed_.title
        filter_class = 'feeds'
        filter_name = f'feed={feed_id}'
        page_title = feed_.title
    elif filter == 'all':
        count = feed.get_all_entries(user, Entry.id).count()
        q = feed.get_all_entries(user)
        panel_title = 'All'
        filter_class = filter_name = 'all'
        page_title = 'All'
    else:  # Default
        count = feed.get_unread_entries(user, Entry.id).count()
        q = feed.get_unread_entries(user)
        panel_title = 'Unread'
        filter_class = filter_name = 'unread'
        page_title = 'Unread'

    # Cleanup namespace
    del r, s

    return q, locals()
