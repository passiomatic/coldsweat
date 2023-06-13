'''
Custom Jinja Filters
'''

from flask import current_app as app
from werkzeug import http
from . import utilities


@app.template_filter('friendly_url')
def friendly_url(value):
    if value:
        return utilities.friendly_url(value)
    return ''


@app.template_filter('datetime')
def datetime(value):
    if value:
        return utilities.format_datetime(value)
    return '—'


@app.template_filter('iso_datetime')
def iso_datetime(value):
    if value:
        return utilities.format_iso_datetime(value)
    return ''


@app.template_filter('date')
def date(value):
    if value:
        return utilities.format_date(value)
    return '—'


@app.template_filter('since')
def datetime_since(value):
    if value:
        return utilities.datetime_since(value)
    return '—'


@app.template_filter('since_today')
def datetime_since_today(value):
    if value:
        return utilities.datetime_since_today(value)
    return '—'


@app.template_filter('epoch')
def epoch(value):
    if value:
        return utilities.datetime_as_epoch(value)
    return '—'


@app.template_filter('status_title')
def status_title(code):
    title = 'Unknown (%s)' % code
    try:
        return http.HTTP_STATUS_CODES[code]
    except KeyError:
        pass
    return title
