'''
Feed autodiscovery tests
'''

from os import path
import pytest
from coldsweat.markup import find_feed_links

test_dir = path.dirname(path.abspath(__file__))


@pytest.mark.parametrize("filename, expected_url", [
    ('discovery/html5-xhtml.html', 'http://example.com/feed'),
    ('discovery/xhtml.html', 'http://somedomain.com/articles.xml'),
    ('discovery/html4-base.html', 'http://somedomain.com/articles.xml'),
    ('discovery/html4-no-base.html', 'http://example.com/articles.xml'),
]
)
def test_discovery(filename, expected_url):
    with open(path.join(test_dir, filename)) as f:
        url, _ = find_feed_link(f.read(), 'http://example.com')
        assert url == expected_url


def find_feed_link(data, base_url):
    links = find_feed_links(data, base_url)
    if links:
        return links[0]
    return None
