Tweet this post
---------------

One obvious integration is to be able to tweet a given post from the
article panel. This is pretty simple by using one of the many Twitter
wrappers out there, like `http://code.google.com/p/python-twitter/`_ or
`https://github.com/Mezgrman/TweetPony`_. This feature is scheduled in a
future release.

Still not sure what kind of auth approach to use. There are
`https://dev.twitter.com/docs/auth/obtaining-access-tokens`_.

One less obvious approach
-------------------------

Unfortunately after the 1.1 API changes it isn't so easy anymore to get
an RSS feed out of one's Twitter stream without recurring to some
third-party software layer, see
`http://blog.fogcat.co.uk/2013/01/17/creating-an-rss-feed-for-your-twitter-home-page/`_
and `https://dev.twitter.com/discussions/4823`_.

Packages like `http://chrissimpkins.github.io/tweetledee/`_ makes easy
to query Twitter and get meaningful RSS/JSON data in return. I can
envision one could install Tweetledee on the same server running
Coldsweat and subscribe to the URL
http://%5Byourdomain%5D/tweetledee/userrss.php

--------------

However, the whole idea to see a Twitter stream as a different form of
RSS feed is appealing so it might be worth to investigate the matter
further.

.. _`http://code.google.com/p/python-twitter/`: pyhton-twitter
.. _`https://github.com/Mezgrman/TweetPony`: TweetPony
.. _`https://dev.twitter.com/docs/auth/obtaining-access-tokens`: many options available
.. _`http://blog.fogcat.co.uk/2013/01/17/creating-an-rss-feed-for-your-twitter-home-page/`: 1
.. _`https://dev.twitter.com/discussions/4823`: 2
.. _`http://chrissimpkins.github.io/tweetledee/`: Tweetledee




