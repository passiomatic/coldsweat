import peewee
import flask
import flask_login
from ..models import User, Feed, Entry, Read
from ..utilities import format_datetime
from . import bp, SessionUser


@bp.route('/login', methods=['GET', 'POST'])
def login():
    next = flask.request.values.get('next')
    if flask.request.method == 'GET':
        return flask.render_template("auth/login.html", next=next, stats=get_stats())

    email = flask.request.form['email']
    password = flask.request.form['password']
    user = User.validate_credentials(email, password)
    if user:
        session_user = SessionUser(user)
        flask_login.login_user(session_user)
        # Check if we redirect within the same server
        if not url_has_allowed_host_and_scheme(next, {flask.request.host}):
            flask.abort(400)        
        return flask.redirect(next or flask.url_for('main.index'))  
    flask.flash('Please check your account credentials and try again.', category="error")    
    return flask.redirect(flask.url_for('auth.login', next=next))



@bp.route('/logout')
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('main.index'))


def get_stats():
    '''
    Get some user-agnostic stats from Coldsweat database
    '''

    last_checked_on = Feed.select(
        peewee.fn.Max(Feed.last_checked_on)).scalar()
    if last_checked_on:
        last_checked_on = format_datetime(last_checked_on)
    else:
        last_checked_on = 'Never'

    namespace = {
        'last_checked_on': last_checked_on,
        'entry_count': Entry.select().count(),
        'unread_entry_count': Entry.select().where(
            ~(Entry.id << Read.select(Read.entry))).count(),
        'feed_count': Feed.select().count(),
        # @@TODO: count enabled feeds with at least one subscriber
        'active_feed_count': Feed.select().where(Feed.enabled==True).count()  # noqa
    }

    return namespace

# From https://github.com/django/django/blob/4.2.2/django/utils/http.py#L256C1-L283C6
def url_has_allowed_host_and_scheme(url, allowed_hosts, require_https=False):
    """
    Return ``True`` if the url uses an allowed host and a safe scheme.

    Always return ``False`` on an empty url.

    If ``require_https`` is ``True``, only 'https' will be considered a valid
    scheme, as opposed to 'http' and 'https' with the default, ``False``.

    Note: "True" doesn't entail that a URL is "safe". It may still be e.g.
    quoted incorrectly. Ensure to also use django.utils.encoding.iri_to_uri()
    on the path component of untrusted URLs.
    """
    if url is not None:
        url = url.strip()
    if not url:
        return False
    if allowed_hosts is None:
        allowed_hosts = set()
    elif isinstance(allowed_hosts, str):
        allowed_hosts = {allowed_hosts}
    # Chrome treats \ completely as / in paths but it could be part of some
    # basic auth credentials so we need to check both URLs.
    return _url_has_allowed_host_and_scheme(
        url, allowed_hosts, require_https=require_https
    ) and _url_has_allowed_host_and_scheme(
        url.replace("\\", "/"), allowed_hosts, require_https=require_https
    )

import unicodedata
import urllib.parse 

def _url_has_allowed_host_and_scheme(url, allowed_hosts, require_https=False):
    # Chrome considers any URL with more than two slashes to be absolute, but
    # urlparse is not so flexible. Treat any url with three slashes as unsafe.
    if url.startswith("///"):
        return False
    try:
        url_info = urllib.parse.urlparse(url)
    except ValueError:  # e.g. invalid IPv6 addresses
        return False
    # Forbid URLs like http:///example.com - with a scheme, but without a hostname.
    # In that URL, example.com is not the hostname but, a path component. However,
    # Chrome will still consider example.com to be the hostname, so we must not
    # allow this syntax.
    if not url_info.netloc and url_info.scheme:
        return False
    # Forbid URLs that start with control characters. Some browsers (like
    # Chrome) ignore quite a few control characters at the start of a
    # URL and might consider the URL as scheme relative.
    if unicodedata.category(url[0])[0] == "C":
        return False
    scheme = url_info.scheme
    # Consider URLs without a scheme (e.g. //example.com/p) to be http.
    if not url_info.scheme and url_info.netloc:
        scheme = "http"
    valid_schemes = ["https"] if require_https else ["http", "https"]
    return (not url_info.netloc or url_info.netloc in allowed_hosts) and (
        not scheme or scheme in valid_schemes
    )