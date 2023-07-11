If you want to run Coldsweat with Ngnix web server you need to bind it
to a socket. This is a modified ``dispatch.fcgi`` file suitable to run
Coldsweat using FastCGI.

\``\` python

#. !/usr/bin/env python """ Boostrap file for FastCGI environments """

try: from flup.server.fcgi_fork import WSGIServer except ImportError,
exc: print 'Error: unable to import Flup package.\nColdsweat needs Flup
to run as a FastCGI process.' raise exc

from coldsweat.app import setup_app

if \__name_\_ == '__main__':
WSGIServer(setup_app(),bindAddress='/tmp/coldsweat-fcgi.sock').run()
\``\`

Then, to have Coldsweat working behind NGinx at "/" (e.g.
http://myhost.example.com/) you change the ``nginx.conf`` file entries
like this:

\``\` location / { root /path/to/coldsweat; include fastcgi_params;
fastcgi_param PATH_INFO $fastcgi_script_name; fastcgi_param SCRIPT_NAME
""; fastcgi_pass 127.0.0.1:7070; }

location /static/ { root /path/to/coldsweat; } \``\`

Then in ``etc/config`` file you set the ``static_url`` setting to:

\``\` static_url: /static \``\`

See also
~~~~~~~~

-  `Using Coldsweat with Gunicorn and Nginx`_
-  `https://github.com/passiomatic/coldsweat/issues/21`_ for more
   information.

.. _Using Coldsweat with Gunicorn and Nginx: Using Coldsweat with Gunicorn and Nginx
.. _`https://github.com/passiomatic/coldsweat/issues/21`: issue #21
