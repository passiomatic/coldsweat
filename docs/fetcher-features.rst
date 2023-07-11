These are some Coldsweat fetcher features worth noting.

HTTP Conditional GET
~~~~~~~~~~~~~~~~~~~~

Ask for feed freshness before doing a regular GET of the data.

Blacklisted sites
~~~~~~~~~~~~~~~~~

Each entry link or image is scanned and if their href or src attributes
match one of the blacklisted sites element is simply removed from the
saved entry. This way most ad tracking/social networks junk are removed
before entry gets delivered to clients.

Follow feed location changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetcher follows "301 Moved Permanently" HTTP status code and update feed
information accordingly. The typical scenario is a feed previously self
hosted then moved to Feedburner - or the other way around.

Disabled feeds
~~~~~~~~~~~~~~

For each feed Coldsweat keeps has an error counter, so after a given
maximum numbers of errors a feed gets disabled. This avoids waste
bandwidth and time by polling dead feeds forever. Fetcher also
understands "410 Gone" HTTP status code and disable feed immediately.
