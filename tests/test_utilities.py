import pytest
import coldsweat.utilities as utilities

def test_truncate():
    assert utilities.truncate('Lorèm ipsum dolor sit ame', 10) == 'Lorèm ips…'


@pytest.mark.parametrize("value, wanted", [
    ('https://example.com', True), # Scheme and hostname only
    ('http://example.org/feed.xml', True),  # With path 
    ('https://user.name:password123@example.com/feed.xml', True),  # With credentials
    ('example.com', False),  # Not URL
]
)
def test_validate_url(value, wanted):
    assert utilities.validate_url(value) == wanted


@pytest.mark.parametrize("value, wanted", [
    ('http://example.org/feed.xml', 'example.org'),
    ('', ''),
] 
)
def test_friendly_url(value, wanted):
    assert utilities.friendly_url(value) == wanted
