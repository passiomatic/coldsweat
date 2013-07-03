# Coldsweat

Coldsweat is a clean-room Python clone of the [Fever RSS aggregator][f], focusing on providing a compatible API and a simple feed store based on SQLite or MySQL. Coldsweat started as a fork of [Bottle Fever][b] by Rui Carmo. By now I revised most of the code and tested the feed fetcher code with hundreds of Atom and RSS feeds. 

![Screenshot](http://lab.passiomatic.com/coldsweat/images/coldsweat-screenshot.jpg)

## Target features

* Multi-user support
* Compatible with Reeder apps on iOS and Mac OS X
* Grouping of similar items
* Minimal web interface to add/import feeds
* Multiprocessing for parallel feed fetching

## Technical underpinnings

* SQLite and MySQL databases (trivial to add Postgres if you want, since it uses the Peewee ORM)
* WSGI compatible, currently tested under CGI, FastCGI and Passenger environments
* Uses Mark Pilgrim's [Universal Feed Parser][fp]

## Current status

Coldsweat correctly syncs read and saved items with Reeder for iOS — see issue #3 for more information. Command-line utilities are provided to import existing feeds as an OPML file and store new feed entries in the database.

## Setup

See <https://github.com/passiomatic/coldsweat/wiki/Setup>



[fp]: https://pypi.python.org/pypi/feedparser/
[f]: http://www.feedafever.com/
[s]: https://github.com/passiomatic/coldsweat
[b]: https://github.com/rcarmo/bottle-fever