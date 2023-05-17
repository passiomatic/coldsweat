First, download Coldsweat or clone the repository into your installation directory. 

== Python version
Starting version 0.9.5 Python 2.7.x is required. 

Actually Coldsweat isn't compatible with Python 3.x. To see what's version of Python is installed in your system run Python with the -V option:
{{{
$ python -V
Python 2.7.9
}}}

**Please note**: feeds using HTTPS protocol are best handled using a //recent// version of Python 2.7.x. I've tested them against 2.7.9 on OS X and they work well, but I've found issues on a deploy machine using 2.7.3.

== Install dependencies

Coldsweat uses various third-party packages:

* Feedparser
* Peewee 
* Requests
* WebOb
* Tempita
* [[Flup|https://pypi.python.org/pypi/flup]], for FastCGI support (optional)
* [[Mysql-python|https://pypi.python.org/pypi/MySQL-python]], for MySQL suppport  (optional)
* [[psycopg2|https://pypi.python.org/pypi/psycopg2]], for PostgreSQL suppport  (optional)

**Note**: you can use [[PyMySQL|https://pypi.python.org/pypi/PyMySQL]] instead of MySQL-python if you have trouble installing the latter.

If you don't have the Pip utility first install it with:
{{{
$ [sudo] easy_install pip
}}}

Then change to the directory where you installed Coldsweat and install all the mandatory dependencies:
{{{
$ cd /path/to/coldsweat
$ [sudo] pip install -r requirements.txt
}}}

== Create the etc/config file
Copy or rename the sample configuration file:
{{{
$ cp etc/config-sample etc/config 
}}}

You may want to take a look at {{{config}}} and tweak few options before proceed. 

== Create the database
Several Coldsweat features can be accessed via the sweat command-line utility. There are a number of available commands, like //setup//:  
{{{
$ python sweat.py setup
}}}

By default the script will create the {{{data/coldsweat.db}}} file using Sqlite as database engine. A default user named //coldsweat// will also be created and you will be asked for an e-mail and a password. 

If you would like to use a different username run the sweat utility with the -u option:
{{{
$ python sweat.py setup -u johndoe
Enter e-mail for user johndoe (needed for Fever sync, hit enter to leave blank): john.d@example.com
Enter password for user johndoe: 
Enter password (again): 
Setup for user johndoe completed.
}}}
You can run again the //setup// command to create as many users you like. 

If you forget your password run setup again with the -w (--password) option to reset it:

{{{
$ python sweat.py setup -w -u coldsweat
Reset password for user coldsweat: 
Enter password (again): 
}}}

== Import and fetch feeds
The //import// command will load a given OPML file and assign it to the default user //coldsweat//:
{{{
$ python sweat.py import /path/to/subscriptions.xml
}}}

The subscriptions file has the same format produced by the Takeout procedure while exporting your Google Reader feeds. 

Again, if you would like to assign imported feeds to a different user run the sweat utility with the -u option:
{{{
$ python sweat.py import -u johndoe /path/to/subscriptions.xml
}}}

For testing purposes there's a sample OPML file called {{{coldsweat/tests/markup/subscriptions.xml}}}. To import it run: 
{{{
$ python sweat.py import coldsweat/tests/markup/subscriptions.xml
}}}

To fetch feeds automatically after import add the {{{-f}}} option:
{{{
$ python sweat.py import -f coldsweat/tests/markup/subscriptions.xml
}}}

To start a feed fetch manually run: 
{{{
$ python sweat.py fetch
}}}

You should use Cron or similar utilities to schedule refreshes on a regular basis.

== Starting a local server
Coldsweat includes an HTTP server to try it out locally. Use the //serve// command to start the server on port 8080:
{{{
$ python sweat.py serve
Serving on http://localhost:8080
^CInterrupted by user
}}}

If you would like to use a different port number specify it with the {{{-p}}} option: 
{{{
$ python sweat.py serve -p 3333
Serving on http://localhost:3333
}}}

== Deploy
Once you have a working Coldsweat installation you are ready to [[deploy it|Deploy]].



