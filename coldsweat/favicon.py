# -*- coding: utf-8 -*-
"""
Decsription: favicon retrieval

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
"""
import base64, urlparse
import requests
from requests.exceptions import RequestException

from coldsweat import log, config

DEFAULT_FAVICON = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAxlBMVEUAAABOWZ5BTZhCTZhHUpt7g7d5gbZ5grZ5grZ6grZsda9sdq9tdq9tdrBtd7Bye7JxerJye7JzfLN0fbNdaKdeaadfaahfaqhha6ldZ6dfaahfaqhjbat3gLV6grZ6grd8hLh/h7mAh7mFjLxfaahgaqlha6libKpjbapRXKBSXKBSXaFTXqFUX6KNmcKXo8idqcujrs6uuNWzvdi5wtu+x96/x97EzOHJ0eXQ1ufV2+vb4O/g5fHm6vXr7/fx9Pv8/f////8y4F8aAAAALnRSTlMACR0dI1BRUVJSiIiIiIi8vb29vdbW1tbW4uLi4uzs7Ozs7Ozx8fHx8f39/f39FstVagAAALBJREFUGBllwUFOw0AMQNFve6Yhk6RFAhZsev9rwRap6iKZtp4kRrCE9+APAZGuvGX8q3oEhtgwHUexYVP2wNByei025qdx8LaF0U1noGWTdlq2VSmlhwgjNht6jPNLcpgU5HGUSyIn1UNWkEbKKCiDBz+EIOGedKpwSOP2aBixP4Pd9hZZP653ZZkrvzzqrWIE3mfRld4/Zw9BrCv9e3hcl+pbGMTaQvb1fpnXPfjnG2UzUabhPViuAAAAAElFTkSuQmCC"

def make_data_uri(content_type, data):
    """
    Return data as a data:URI scheme
    """
    return "data:%s;base64,%s" % (content_type, base64.urlsafe_b64encode(data))

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