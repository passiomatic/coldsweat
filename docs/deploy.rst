There are several ways to deploy Coldsweat on a "production" server.
Here you can find the most common ones like FastCGI and less common like
Passenger and Gunicorn+Nginx.

Deploy using CGI and Apache (slow, not recommended)
---------------------------------------------------

Deploy using CGI and Apache's VirtualHost directive is pretty
straightforward.

::

   <VirtualHost *:80>
       DocumentRoot "/path/to/coldsweat/static"
       ServerName yourdomain.tld

       # Set up CGI handler
       AddHandler cgi-script .cgi
       Options +FollowSymLinks +ExecCGI

       DirectoryIndex index.cgi
       ScriptAlias /index.cgi /path/to/coldsweat/index.cgi/
   </VirtualHost>

First set site root to the Coldsweat ``static`` directory, so
configuration settings and database files won't be exposed to the web.
Then the ScriptAlias directive maps the index file to the ``/index.cgi``
request.

Finally make sure index file is executable by issuing a *chmod* command:

::

   chmod 755 index.cgi

Deploy using FastCGI and Apache
-------------------------------

Deploy using FastCGI and Apache's VirtualHost directive is also
straightforward and quite similar to the CGI deploy.

::

   <VirtualHost *:80>
       DocumentRoot "/path/to/coldsweat/static"
       ServerName yourdomain.tld

       # Set up FastCGI handler
       AddHandler fastcgi-script .fcgi
       Options +FollowSymLinks +ExecCGI

       DirectoryIndex dispatch.fcgi
       ScriptAlias /dispatch.fcgi /path/to/coldsweat/dispatch.fcgi/
   </VirtualHost>

As usual the ``dispatch.fcgi`` file must have executable permissions.

Deploy using Passenger
----------------------

See `Deploy on DreamHost`_.

Deploy using Gunicorn and Nginx
-------------------------------

-  See `Using Coldsweat with Nginx`_
-  See `Using Coldsweat with Gunicorn and Nginx`_

.. _Deploy on DreamHost: Deploy on DreamHost
.. _Using Coldsweat with Nginx: Using Coldsweat with Nginx
.. _Using Coldsweat with Gunicorn and Nginx: Using Coldsweat with Gunicorn and Nginx
