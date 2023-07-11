import os
import re
import urllib.request
import urllib.parse
import urllib.error
from hashlib import md5, sha1
import base64
from calendar import timegm
from datetime import datetime

# --------------------
# String utilities
# --------------------


def encode(value):
    return value.encode('utf-8', 'replace')


def truncate(value, max_length):
    """
    Return a truncated string for value if value length is > max_length
    """
    if len(value) < max_length:
        return value
    return value[:max_length-1] + '…'


def make_data_uri(content_type, data):
    """
    Return data as a data:URI scheme
    """
    return "data:%s;base64,%s" % (content_type,
                                  base64.standard_b64encode(data).decode('utf-8'))


# --------------------
# Hash functions
# --------------------

def make_md5_hash(s):
    return md5(encode(s)).hexdigest()


def make_sha1_hash(s):
    return sha1(encode(s)).hexdigest()


def make_nonce():
    nonce = os.urandom(16)
    return nonce.hex()

# --------------------
# URL utilities
# --------------------


BLACKLIST_QS = ["utm_source", "utm_campaign", "utm_medium",
                "utm_content", "utm_cid", "utm_term",
                "piwik_campaign", "piwik_kwd"]

# Lifted from https://github.com/django/django/\
#        blob/master/django/core/validators.py
RE_URL = re.compile(
    r'^https?://'               # http:// or https://
    r'(?:[^:@/]+:[^:@/]+@)?'    # credentials
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain..
    r'localhost|'                           # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'                            # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)
#  @@TODO: Add IPv6


def validate_url(value):
    return value and (RE_URL.search(value)is not None)


def scrub_url(url):
    '''
    Clean query string arguments
    '''
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)
    d = urllib.parse.parse_qs(query)
    d = dict((k, v) for k, v in list(d.items()) if k not in BLACKLIST_QS)
    return urllib.parse.urlunsplit((scheme, netloc, path,
                                    urllib.parse.urlencode(d, doseq=True), fragment))


def friendly_url(url):
    u = urllib.parse.urlsplit(url)
    return u.hostname or ''

# --------------------
# Date/time functions
# --------------------


def datetime_as_epoch(value):
    return int(timegm(value.utctimetuple()))


def tuple_as_datetime(value):
    return datetime.utcfromtimestamp(timegm(value))


# Weekday and month names for HTTP date/time formatting; always English!
_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None,  # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_http_datetime(value):
    """
    Format datetime to comply with RFC 1123
    (ex.: Fri, 12 Feb 2010 16:23:03 GMT).
    Assume GMT values
    """
    year, month, day, hh, mm, ss, wd, y, z = value.utctimetuple()
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        _weekdayname[wd], day, _monthname[month], year, hh, mm, ss
    )


def format_iso_datetime(value):
    # Unlike datetime.isoformat() assume UTC
    return format_datetime(value, format='%Y-%m-%dT%H:%M:%SZ')


def format_datetime(value, format='%a, %b %d at %H:%M'):
    return value.strftime(format)


def format_date(value):
    return format_datetime(value, '%b %d, %Y')


def datetime_since(value, comparison_value, default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """

    diff = comparison_value - value

    periods = (
        (diff.days // 365, "year", "years"),
        (diff.days // 30, "month", "months"),
        (diff.days // 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds // 3600, "hour", "hours"),
        (diff.seconds // 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)

    return default


def datetime_since_today(value, comparison_value=None):
    """
    Returns string representing "date since" e.g.
    today, yesterday and Wed, Jan 29
    """

    comparison_value = comparison_value or datetime.utcnow()
    delta = comparison_value - value
    if delta.days == 0:
        return 'today'
    elif delta.days == 1:
        return 'yesterday'

    # Earlier date
    return format_date(value)

