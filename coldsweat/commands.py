# -*- coding: utf-8 -*-
"""
Description: sweat utility commands

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
"""
import os, sys, ssl
from ssl import CERT_NONE, OP_NO_COMPRESSION, PROTOCOL_TLS
from optparse import OptionParser, make_option
from getpass import getpass
import readline

from wsgiref.simple_server import *
from webob.static import DirectoryApp
from peewee import OperationalError

from coldsweat import *
from models import *
from controllers import *
from app import *

import cascade, fever, frontend
from utilities import render_template
from plugins import trigger_event, load_plugins
import filters 

# Ensure all web server activity is logged on stdout 
#   and not stderr like default WSGIRequestHandler
class WSGIRequestHandler_(WSGIRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write("%s - - [%s] %s\n" %
                         (self.client_address[0],
                          self.log_date_time_string(),
                          format%args))
                          
                          
class CommandError(Exception):
    pass

class CommandController(FeedController, UserController):
    
    def _get_user(self, username):
        try:
            user = User.get(User.username == username)
        except User.DoesNotExist:
            raise CommandError('unable to find user %s. Use -u option to specify a different user' % username)
    
        return user


    def run_command(self, name, options, args):    
        try:
            handler = getattr(self, 'command_%s' % name)
        except AttributeError:
            raise CommandError('unrecognized command %s, use the -h option for a list of available commands' % name)

        handler(options, args)
        
    # Feeds
     
    def command_import(self, options, args):
        '''Imports feeds from OPML file'''
    
        if not args:
            raise CommandError('no input OPML file given')
    
        self.user = self._get_user(options.username)
    
        feeds = self.add_feeds_from_file(args[0])
        for feed, group in feeds:
            self.add_subscription(feed, group)      
        if options.fetch_data:
            # Fetch just imported feeds
            self.fetch_feeds([feed for feed, group in feeds]) 
        
        print "Import%s completed for user %s. See log file for more information" % (' and fetch' if options.fetch_data else '', self.user.username)

    def command_export(self, options, args):
        self.user = self._get_user(options.username)
        if options.saved_entries:
            self._export_saved_entries(options, args)
        else:
            self._export_feeds(options, args)
        
        print "Export completed for user %s." % self.user.username
        
    def _export_feeds(self, options, args):
        '''Exports feeds to OPML file'''
    
        if not args:
            raise CommandError('no output OPML file given')
    
        filename = args[0]
        #@@TODO Use a 'http_datetime' filter in template instead
        timestamp = format_http_datetime(datetime.utcnow())        
        groups = [ (group.title, self.get_group_feeds(group)) for group in self.get_groups() ]
        
        with open(filename, 'w') as f:
            f.write(render_template(os.path.join(template_dir, 'export.xml'), locals()))

    def _export_saved_entries(self, options, args):
        '''Exports saved entries to Atom file'''
        
        if not args:
            raise CommandError('no output Atom file given')
        
        filename = args[0]    
        timestamp = datetime.utcnow()        
        q = self.get_saved_entries()
        guid = FEED_TAG_URI % (timestamp.year, make_sha1_hash(self.user.email or self.user.username))
        version = VERSION_STRING

        with open(filename, 'w') as f:
            f.write(render_template(os.path.join(template_dir, 'export-saved.xml'), locals(), filters))
            

    def command_refresh(self, options, args):
        '''Starts a feeds refresh procedure'''
    
        self.fetch_all_feeds()
        print 'Fetch completed. See log file for more information'
    
    command_fetch = command_refresh # Alias

    # Local server

    def command_serve(self, options, args):
        '''Starts a local server'''
        
        # Determine the address to bind
        address = '0.0.0.0' if options.allow_remote_access else 'localhost'
        
        # Determine the schemes to serve
        # Limitation: the default WSGI server can only serve a single scheme with a single instance...
        https_only = hasattr(options, 'https_only') and options.https_only
        https = True if https_only else False # or (hasattr(options, 'ssl') and options.ssl) 
        http = not https_only
        
        # If we are to serve HTTPS, we need to make sure that basic things are configured properly
        if https:
            # Note: newer versions of OpenSSL employ pretty much all of these settings by default. They are
            # aimed at old python versions, with old OpenSSL versions and defaults.
            # See also:
            #    https://docs.python.org/2/library/ssl.html
            
            # First and foremost
            ssl_protocols = PROTOCOL_TLS
            ssl_context = ssl.SSLContext(ssl_protocols)
            ssl_context.options |= ssl.OP_NO_SSLv2      # disable SSLv2 (always!)
            ssl_context.options |= ssl.OP_NO_SSLv3      # disable SSLv3 (always!)
            ssl_context.options |= OP_NO_COMPRESSION    # try to disable TLS compression (BUT SOMEHOW, IT DOESN'T WORK!)
            
            # Let's specify allowed/disallowed cipher suites now. For reference on how to
            # construct the value, refer to:
            #     https://wiki.openssl.org/index.php/Manual:Ciphers(1)
            #     https://www.owasp.org/index.php/Transport_Layer_Protection_Cheat_Sheet
            # Note: optionally and for more security, I recommend applying '!SHA1' too as
            # there are known attacks against this cryptographic hash function and plans
            # are in motion for it to be deprecated in regard to the SSL/TLS protocols.
            # Globally trusted certificate authorities shouldn't issue certificates with
            # SHA1 anymore and I believe some browsers have disabled it already. For more
            # information, see:
            #     https://www.entrust.com/sha-1-2017/
            ssl_context.set_ciphers('HIGH:MEDIUM:!LOW:!EXP:!PSK:!ADH:!AECDH:!DES:!3DES:!IDEA:!MD5:!RC2:!RC4:!SEED:!aNULL:!eNULL:!NULL')
        
        # Override the 'Cascade' class to fix behavior of the default WSGI server
        # Note: if the 'http' and 'https' fields are shared, this code can easily be moved
        # to the original location (Cascade class).
        class WSGI_HTTPS_Cascade(cascade.Cascade):
            def __call__(self, environ, start_response):
                if https:
                    # We know that because of a limitation in the default WSGI server, we can only serve HTTPS.
                    # However, even for HTTPS request, value for 'wsgi.url_scheme' is set to 'http'. To fix this,
                    # we need to force 'https' before control reaches a handler:
                    environ['wsgi.url_scheme'] = 'https'
                        
                # DEBUG: now would be a good time to print request info, if desired
                # Note: optionally, this behavior could be triggered by the user setting
                # a log level of DEBUG in the configuration file.
                # print "\n-> INCOMING REQUEST:"
                # dump_environ(environ)    # to print only interesting fields
                # dump_obj(environ)        # to print the dictionary fully 
                    
                # Done... resume with the original __call__ implementation
                return super(WSGI_HTTPS_Cascade, self).__call__(environ, start_response)
        
        # Create a middleware app to serve static content  
        static_app = DirectoryApp(os.path.join(installation_dir, "static"), index_page=None)
        
        # Create a cascade app to first look for static content, and then for Coldsweat apps
        # cascade_app = ExceptionMiddleware(cascade.Cascade([static_app, fever.setup_app(), frontend.setup_app()]))
        cascade_app = ExceptionMiddleware(WSGI_HTTPS_Cascade([static_app, fever.setup_app(), frontend.setup_app()]))
        
        # Prepare the server
        httpd = make_server(address, options.port, cascade_app,  WSGIServer, WSGIRequestHandler_)
        
        # TODO:
        # The 'httpd.socket' object could probably be monkey-patched to perform a server redirect (302) when
        # we receive an HTTP request while we can only serve HTTPS responses. In that case, special attention
        # must be paid to compatibility with the 'ssl.wrap_socket' function. Personally, I would advice against
        # such attempts as it shouldn't be completely trivial. Instead, using a web server capable of such
        # basic things is recommended.
        # Presently, Firefox tells us:
        #     'The connection to the server was reset while the page was loading.'
        # It means that client connections are always accepted but as soon as the server realizes it won't see
        # a proper SSL/TLS handshake initiation (it receives plain HTTP request instead), it will reset (close?)
        # the connection.
        
        # If we are to serve HTTPS, we need a special setup
        if https:
            # Test that the certificate and a corresponding private key are configured and exist
            # Note: other software should be responsible for validating the content (at runtime)
            cert = config.web.path_cert
            if (cert is None) or (cert == ""):
                raise ValueError("Server certificate has not been configured.") 
            cert = cert if os.path.isabs(cert) else os.path.join(installation_dir, cert)
            if not os.path.exists(cert):
                raise ValueError("Server certificate not found at: '%s'." % cert)
            
            key = config.web.path_cert_key
            if (key is None) or (key == ""):
                raise ValueError("Server certificate's private key has not been configured.") 
            key = key if os.path.isabs(key) else os.path.join(installation_dir, key)
            if not os.path.exists(key):
                raise ValueError("Server certificate's private key not found at: '%s'." % key)
            
            # Enable SSL/TLS (HTTPS) with the server
            httpd.socket = ssl.wrap_socket (
                # See also: https://docs.python.org/2/library/ssl.html
                
                # The socket to wrap
                httpd.socket,
                
                # The private key
                keyfile=key,
                
                # The certificate
                certfile=cert,
                
                # Act as a server in SSL/TLS
                server_side=True,
                
                # Which protocols to allow
                ssl_version=ssl_protocols,
                
                # Don't require/validate client certificates
                cert_reqs=CERT_NONE,
                
                # We don't need to supply certificate authorities to validate client certificates
                ca_certs=None)
        
        # Print how to access Coldsweat 
        if http and https:
            # This is not supported at present time and should never happen
            print 'Serving on http(s)://%s:%s' % (address, options.port)
        elif http:
            print 'Serving on http://%s:%s' % (address, options.port)
        else:
            print 'Serving on https://%s:%s' % (address, options.port)
        
        # Launch the server
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print 'Interrupted by user'            
    
    # Setup and update
 
    def command_setup(self, options, args):
        '''Setup a working database'''
        username = options.username        
            
        setup_database_schema()

        def get_password(label):
            while True:
                password = read_password(label)
                if not User.validate_password(password):
                    print 'Error: password should be at least %d characters long' % User.MIN_PASSWORD_LENGTH
                    continue        
                password_again = read_password("Enter password (again): ")
                if password != password_again:
                    print "Error: passwords do not match, please try again"
                else:
                    return password

        # Just reset user password
        if options.reset_password:
            try:
                user = User.get(User.username == username)
            except User.DoesNotExist:
                raise CommandError('unknown user %s, please select another username with the -u option' % username)

            password = get_password("Reset password for user %s: " % username)
            user.password = password
            user.save()
            return 
    
        # Regular setup process. Check if username is already in use
        try:
            User.get(User.username == username)
            raise CommandError('user %s already exists, please select another username with the -u option' % username)
        except User.DoesNotExist:
            pass
    
        email = raw_input('Enter e-mail for user %s (needed for Fever sync, hit enter to leave blank): ' % username)
        password = get_password("Enter password for user %s: " % username)
    
        User.create(username=username, email=email, password=password)
        print "Setup completed for user %s." % username

    def command_upgrade(self, options, args):
        '''Upgrades Coldsweat internals from a previous version'''
        
        try:
            if migrate_database_schema():
                print 'Upgrade completed.'
            else:
                print 'Database is already up-to-date.'
        except OperationalError, ex:         
            logger.error(u'caught exception updating database schema: (%s)' % ex)
            print  'Error while running database update. See log file for more information.'

    command_update = command_upgrade # Alias

def read_password(prompt_label="Enter password: "):
    if sys.stdin.isatty():
        password = getpass(prompt_label)
    else:
        # Make script be scriptable by reading password from stdin
        print prompt_label
        password = sys.stdin.readline().rstrip()

    return password
    
COMMANDS = 'import export serve setup upgrade fetch'.split()    

def run():

    epilog = "Available commands are: %s" % ', '.join(sorted(COMMANDS))
    usage='%prog command [options] [args]'

    available_options = [
        make_option('-s', '--saved-entries',
            dest='saved_entries', action='store_true', help='export saved entries'),

        make_option('-u', '--username', 
            dest='username', default=User.DEFAULT_USERNAME, help="specifies a username (default is %s)" % User.DEFAULT_USERNAME),

        make_option('-w', '--password',
            dest='reset_password', action='store_true', help='reset a user password'),

        make_option('-f', '--fetch',
            dest='fetch_data', action='store_true', help='fetches each feed data after import'),

        make_option('-p', '--port', default='8080', 
            dest='port', type='int', help='specifies the port to serve on (default 8080)'),

        make_option('-r', '--allow-remote-access', action='store_true', dest='allow_remote_access', help='binds to 0.0.0.0 instead of localhost'),
        
        # TODO: the default WSGI web server is not capable of doing this with a single server instance - switch to (e.g.) CherryPy
        # make_option('--ssl', action='store_true', dest='ssl', help='serve under both http:// and https://'),
        
        make_option('--https-only', action='store_true', dest='https_only', help='serve ONLY under https:// (no redirection from http://)'),
    ]
        
    parser = OptionParser(option_list=available_options, usage=usage, epilog=epilog)
     
    command_options, args = parser.parse_args()
    if not args:
        parser.error('no command given, use the -h option for a list of available commands')
        
    command_name, command_args = args[0].lower(), args[1:]

    connect()
    cc = CommandController()
    try:
        cc.run_command(command_name, command_options, command_args)
    except CommandError, ex:
        parser.error(ex)
    finally:
        close()
        # Flush and close all logging handlers
        import logging
        logging.shutdown()
