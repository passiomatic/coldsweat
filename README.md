# Coldsweat

Coldsweat is a clean-room Python clone of the [Fever RSS aggregator][f], focusing on providing a compatible API, a web feed reader and a simple feed store based on SQLite or MySQL. 

Coldsweat started as a fork of [Bottle Fever][b] by Rui Carmo. By now I revised most of the code and tested the feed fetcher code with hundreds of Atom and RSS feeds. 

![Screenshot](http://lab.passiomatic.com/coldsweat/images/coldsweat-0.9.0-screenshot.jpg)

## Motivation

I'm fed up of online services that are here today and gone tomorrow. After the Google Reader shutdown is clear to me that the less we rely on external services the more the data we care about are preserved. With this in mind I'm writing Coldsweat. It will be my personal take at consuming feeds today. 

There will be blood.

## Target features

* Multi-user support
* Compatible with existing Fever desktop and mobile clients
* Support for grouping of similar items
* Multiprocessing for parallel feed fetching
* Web interface to read, add and import feeds

## Technical underpinnings

* Uses the industry standard Mark Pilgrim's [Universal Feed Parser][fp]
* SQLite and MySQL databases (trivial to add Postgres if you want, since it uses the Peewee ORM)
* WSGI compatible - currently tested under CGI, FastCGI and Passenger environments

For more information about the Coldsweat feed fetcher see the _[fetcher features][ff]_ page.

## Current status

* Coldsweat correctly syncs read and saved items with [Reeder][r] for iOS and [ReadKit][rk] on OS X — also see issue #3
* After the 0.8.2 release in the **master** branch I've recently merged a brand new web UI to add and consume feeds. It's still rough around the edges but it will get better
* A command-line utility is provided to bulk import and export feeds as an OPML file, create users and store new feed entries in the database

## Setup

See _[setup]_ page.



[fp]: https://pypi.python.org/pypi/feedparser/
[f]: http://www.feedafever.com/
[s]: https://github.com/passiomatic/coldsweat
[b]: https://github.com/rcarmo/bottle-fever
[rk]: http://readkitapp.com/
[r]: http://reederapp.com/
[ff]: https://github.com/passiomatic/coldsweat/wiki/Fetcher-features
[setup]: https://github.com/passiomatic/coldsweat/wiki/Setup