'''
HTML markup tests
'''
from os import path
import pytest
from coldsweat.markup import (BaseProcessor, strip_html, scrub_html)
import feedparser


BLACKLIST = "feedsportal.com feeds.feedburner.com".split()
test_dir = path.dirname(path.abspath(__file__))


@pytest.mark.parametrize("filename, unwanted", [
    ('markup/sample1.xml', BLACKLIST[0]),
    ('markup/sample1.xml', BLACKLIST[1])
])
def test_scrub(filename, unwanted):
    soup = feedparser.parse(path.join(test_dir, filename))
    for entry in soup.entries:
        data = scrub_html(entry.description, BLACKLIST)
        assert data.count(unwanted) == 0


@pytest.mark.parametrize("value, wanted", [
    ('a', 'a'),  # Identity
    ('a <p class="c"><span>b</span></p> a', 'a b a'),
    (u'à <p class="c"><span>b</span></p> à', u'à b à'),  # Unicode
    ('a&amp;a&lt;a&gt;',
     'a&a<a>'),  # Test unescape of entity and char reference too
    ('<span>a</span>', 'a'),
    ('<span>a', 'a'),  # Unclosed elements
    ('<p><span>a</p>', 'a'),
    ('<foo attr=1><bar />a</foo>', 'a'),  # Non HTML tags
]
)
def test_stripping_html(value, wanted):
    assert strip_html(value) == wanted


@pytest.mark.parametrize("file_in, file_out", [
    ('markup/in.xml', 'markup/out.xml'),
    ('markup/iframe-in.xml', 'markup/iframe-out.xml'),
]
)
def test_processor(file_in, file_out):

    # Use xhtml_mode to match Feedpaser output
    processor = BaseProcessor(xhtml_mode=True)
    soup_in = feedparser.parse(path.join(test_dir, file_in))
    soup_out = feedparser.parse(path.join(test_dir, file_out))
    entry_in_0 = soup_in.entries[0]
    entry_out_0 = soup_out.entries[0]
    processor.reset()
    processor.feed(entry_in_0.content[0].value)
    assert processor.get_output() == entry_out_0.content[0].value


@pytest.mark.parametrize("file_in, file_out", [
    ('markup/bad-iframe-in.xml', 'markup/bad-iframe-out.xml')
]
)
def test_processor_2(file_in, file_out):

    # Use xhtml_mode to match Feedpaser output
    processor = BaseProcessor(xhtml_mode=True)
    soup_in = feedparser.parse(path.join(test_dir, file_in))
    soup_out = feedparser.parse(path.join(test_dir, file_out))
    entry_in_0 = soup_in.entries[0]
    entry_in_1 = soup_in.entries[1]
    entry_out_0 = soup_out.entries[0]
    entry_out_1 = soup_out.entries[1]
    processor.reset()
    processor.feed(entry_in_0.content[0].value)
    assert processor.get_output() == entry_out_0.content[0].value
    processor.reset()
    processor.feed(entry_in_1.content[0].value)
    assert processor.get_output() == entry_out_1.content[0].value
