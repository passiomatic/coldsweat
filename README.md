# Coldsweat

Coldsweat is a clean-room Python clone of the [Fever RSS aggregator][f], focusing on providing a compatible API and a simple feed store based on SQLite.

Coldsweat started as a fork of Bottle Fever by Rui Carmo. By now I revised most of the code and tested the feed fetcher code with hundreds of Atom and RSS feeds. 

Since Coldsweat is intended for personal use — but you can have multiple users/accounts - I dropped the more speedier `speedparser` module to simplify the code.


## Target features

* Multi-user support
* Compatible with Reeder apps on iOS and Mac OS X
* Grouping of similar items
* Minimal web interface to add/import feeds

## Technical underpinnings

* SQLite database (trivial to replace if you want to scale up, since it uses the Peewee ORM)
* WSGI compatible, currently tested under FastCGI environments
* Multiprocessing for parallel feed fetching
* Uses Mark Pilgrim's [`feedparser`][fp]

## Setup

@@TODO

### Dependences

Coldsweat uses various third-party packages:

* Feedparser
* Peewee, object-relational mapper 
* Requests
* WebOb
* Tempita, HTML templating

If you don't have the `pip` utility first install it with:

    easy_install pip

Then install all dependences by typing:

    pip install -r requirements.txt


## On the web 

### Project home

@@TODO

### Source code

[Available on GitHub][s].



[p]: https://github.com/coleifer/peewee
[fp]: https://pypi.python.org/pypi/feedparser/
[f]: http://www.feedafever.com/
[s]: https://github.com/passiomatic/coldsweat