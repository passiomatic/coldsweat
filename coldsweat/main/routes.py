import flask
import flask_login
from coldsweat.models import (User, Feed, Group, Entry, Read, Saved)
from playhouse.flask_utils import get_object_or_404
import coldsweat.feed as feed
from coldsweat.main import bp

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
    user = User.get(flask_login.current_user.id)
    query, view_variables = _make_view_variables(user)

    view_variables.update({
        'entries': query.order_by(
            Entry.last_updated_on.desc()
        ).offset(offset).limit(ENTRIES_PER_PAGE),
        'offset': offset + ENTRIES_PER_PAGE,
        'prev_date': flask.request.args.get('prev_date', None),
    })

    return flask.render_template("main/entries.html", **view_variables)


@bp.route('/entries/<int:entry_id>')
@flask_login.login_required
def entry(entry_id):
    entry = get_object_or_404(Entry, (Entry.id == entry_id))

    user = User.get(flask_login.current_user.id)
    
    feed.mark_entry(user, entry, 'read')
    query, view_variables = _make_view_variables(user)
    n = query.where(Entry.last_updated_on < entry.last_updated_on).order_by(
        Entry.last_updated_on.desc()).limit(1)

    view_variables.update({
        'entry': entry,
        'page_title': entry.title,
        'next_entries': n,
        'count': 0  # Fake it
    })

    return flask.render_template('main/entry.html', **view_variables)


@bp.route('/feeds')
@flask_login.login_required
def feed_list():
    '''
    Show subscribed feeds
    '''
    offset, group_id, feed_id, filter_class, panel_title, page_title = \
        0, 0, 0, 'feeds', 'Feeds', 'Feeds'

    offset = flask.request.args.get('offset', 0, type=int)
    user = User.get(flask_login.current_user.id)
    max_errors = 100
    groups = feed.get_groups(user)
    count, query = feed.get_feeds(user, Feed.id).count(), feed.get_feeds(user)
    feeds = query.order_by(Feed.title).offset(offset).limit(FEEDS_PER_PAGE)
    offset += FEEDS_PER_PAGE

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
    user = User.get(flask_login.current_user.id)
    count, query = feed.get_groups(user).count(), feed.get_groups(user)
    groups = query.offset(offset).limit(GROUPS_PER_PAGE)
    offset += GROUPS_PER_PAGE

    return flask.render_template('main/groups.html', **locals())


def _make_view_variables(user):

    count, group_id, feed_id, filter_name, \
        filter_class, panel_title, page_title = 0, 0, 0, '', '', '', ''

    groups = feed.get_groups(user)
    r = Entry.select(Entry.id).join(Read).where((Read.user
                                                 == user)).objects()
    s = Entry.select(Entry.id).join(Saved).where((Saved.user
                                                  == user)).objects()
    read_ids = dict((i.id, None) for i in r)
    saved_ids = dict((i.id, None) for i in s)

    if 'saved' in flask.request.args:
        count = feed.get_saved_entries(user, Entry.id).count()
        q = feed.get_saved_entries(user)
        panel_title = 'Saved'
        filter_class = filter_name = 'saved'
        page_title = 'Saved'
    elif 'group' in flask.request.args:
        group_id = int(flask.request.args['group'])
        group = Group.get(Group.id == group_id)
        count = feed.get_group_entries(user, group, Entry.id).count()
        q = feed.get_group_entries(user, group)
        panel_title = group.title
        filter_class = 'groups'  # The same when listing group
        filter_name = f'group={group_id}'
        page_title = group.title
    elif 'feed' in flask.request.args:
        feed_id = int(flask.request.args['feed'])
        feed_ = Feed.get(Feed.id == feed_id)
        count = feed.get_feed_entries(user, feed_, Entry.id).count()
        q = feed.get_feed_entries(user, feed)
        panel_title = feed_.title
        filter_class = 'feeds'
        filter_name = f'feed={feed_id}'
        page_title = feed_.title
    elif 'all' in flask.request.args:
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

# ---------
# User auth
# ---------


class SessionUser(flask_login.UserMixin):
    '''
    A user in the urrent web session. We cannot mix model.User with 
      flask_login.UserMixin due to methdod names clashing.
    '''

    def __init__(self, user):
        self.id = user.id
        # TODO: Use display_name
        self.display_name = user.username


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return flask.render_template("login.html")

    email = flask.request.form['email']
    password = flask.request.form['password']
    user = User.validate_credentials(email, password)
    if user:
        session_user = SessionUser(user)
        flask_login.login_user(session_user)
        return flask.redirect(flask.url_for('main'))

    return 'Bad login'


@bp.route('/logout')
def logout():
    flask_login.logout_user()
    return 'Logged out'
