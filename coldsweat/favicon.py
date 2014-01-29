# -*- coding: utf-8 -*-
"""
Decsription: favicon retrieval

Copyright (c) 2013—2014 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
"""
import base64, urlparse
import requests
from requests.exceptions import RequestException

from coldsweat import log, config

DEFAULT_FAVICON = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAUtJREFUeNqk089HBGEcx/G2SaeoS0RERJElusbSIUUmsfQHFOm8lyLaUpT+hSKt0l5K2bRESod0LVIs3Yuuy5J6f/nM+Japlh5enpl5Zj/z/PhuaiOfb/hPa1KfxTSecYMyXusJaFQ/jFHMYRcvOEOm3oArPH0bs8BLHKLjr4Ai+pDCGLZR09gkbpH+LcA3W/8M+nGiZ124TgqJAmztdzhAiAAVTGBB77SihPakgLRM4Vhr79bYuguxmWwlBRRwiqruhzSjrAs50nWo8S8BdvbjaMOiNrAFe+4oc25jl3/aRHthDSO6btaUAxVZQe9loqONAjrxiA/Mqy5WNNajo7S2rz7QUuIAK+NeXa/qy5uunENXcFW38XGAr8KKpl/TD6wNqn/XUqKZxX+mor42gB0XtoQ33LtnOS3p3AdYuxDfHjCbUKnl6OZTgAEAR+pHH9rWoLkAAAAASUVORK5CYII="

def make_data_uri(content_type, data):
    """
    Return data as a data:URI scheme
    """
    return "data:%s;base64,%s" % (content_type, base64.standard_b64encode(data))

def google_fetcher(url):
    """
    Fetch the favicon via Google services
    """
    endpoint = "http://www.google.com/s2/favicons?domain=%s" % urlparse.urlparse(url).hostname

#     headers = {
#         'User-Agent': config.get('fetcher', 'user_agent')
#     }
    try:
        result = requests.get(endpoint)
    except RequestException, exc:
        log.warn("could not fetch favicon for %s (%s)" % (url, exc))
        return DEFAULT_FAVICON

    return make_data_uri(result.headers['Content-Type'], result.content)

# Alias
fetch = google_fetcher