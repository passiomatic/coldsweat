# -*- coding: utf-8 -*-
"""
Description: sweat utility commands

Copyright (c) 2013—2014 Andrea Peltrin
License: MIT (see LICENSE for details)
"""
import os
from optparse import OptionParser, make_option
from getpass import getpass
import readline

from wsgiref.simple_server import make_server
from webob.static import DirectoryApp

from coldsweat import *
from models import *
from controllers import *
from app import *

import cascade, fever, frontend
from utilities import render_template
from plugins import trigger_event, load_plugins


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
            raise CommandError('no OPML file given')
    
        self.user = self._get_user(options.username)
    
        feeds = self.add_feeds_from_file(args[0])
        for feed, group in feeds:
            self.add_subscription(feed, group)
    
        print "%d feeds imported for user %s. See log file for more information." % (len(feeds), self.user.username)


    def command_export(self, options, args):
        '''Exports feeds to OPML file'''
    
        if not args:
            raise CommandError('no OPML file given')
    
        self.user = self._get_user(options.username)
    
        filename = args[0]
        
        timestamp = format_http_datetime(datetime.utcnow())
        feeds = Feed.select().join(Subscription).where(Subscription.user == self.user).distinct().order_by(Feed.title)
        
        with open(filename, 'w') as f:
            f.write(render_template(os.path.join(template_dir, 'export.xml'), locals()))
            
        print "%d feeds exported for user %s" % (feeds.count(), self.user.username)    


    def command_refresh(self, options, args):
        '''Starts a feeds refresh procedure'''
    
        self.fetch_all_feeds()
        print 'Refresh completed. See log file for more information'

    # Local server

    def command_serve(self, options, args):
        '''Starts a local server'''
    
        static_app = DirectoryApp("static", index_page=None)
        
        # Create a cascade that looks for static files first, 
        #  then tries the other apps
        cascade_app = ExceptionMiddleware(cascade.Cascade([static_app, fever.setup_app(), frontend.setup_app()]))
        
        address = '0.0.0.0' if options.allow_remote_access else 'localhost'        
        httpd = make_server(address, options.port, cascade_app)
        print 'Serving on http://%s:%s' % (address, options.port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print 'Interrupted by user'            
    
    # Setup and update
 
    def command_setup(self, options, args):
        '''Sets up a working database'''
        username = options.username
    
        setup_database_schema()
    
        # Check if username is already in use
        try:
            User.get(User.username == username)
            raise CommandError('user %s already exists, please select another username with the -u option' % username)
        except User.DoesNotExist:
            pass
    
        email = raw_input('Enter e-mail for user %s (hit enter to leave blank): ' % username)
            
        while True:        
            password = getpass('Enter password for user %s: ' % username)
            if not User.validate_password(password):
                print 'Error: password should be at least %d characters long' % User.MIN_PASSWORD_LENGTH
                continue        
            password_again = getpass('Enter password (again): ')
            
            if password != password_again:
                print 'Error: passwords do not match, please try again'
            else:
                break
    
        User.create(username=username, email=email, password=password)
        print "Setup for user %s completed." % username

    def command_update(self, options, args):
        '''Update Coldsweat internals from a previous version'''
        
        try:
            if migrate_database_schema():
                print 'Update completed.'
            else:
                print 'Database is already up-to-date.'
        except OperationalError, ex:         
            logger.error(u'caught exception updating database schema: (%s)' % ex)
            print  'Error while running database update. See log file for more information.'

def run():

    default_username, _ = User.DEFAULT_CREDENTIALS

    epilog = "Available commands are: %s" % ', '.join(sorted('import export serve setup upgrade refresh'.split()))
    usage='%prog command [options] [args]'

    available_options = [
        make_option('-u', '--username', 
            dest='username', default=default_username, help="specifies a username (default is %s)" % default_username),
#         make_option('-f', '--force',
#             dest='force', action='store_true', help='attempts to refresh even disabled feeds'),
        make_option('-p', '--port', default='8080', 
            dest='port', type='int', help='the port to serve on (default 8080)'),
        make_option('-r', '--allow-remote-access', action='store_true', dest='allow_remote_access', help='binds to 0.0.0.0 instead of localhost'),
    ]
        
    parser = OptionParser(option_list=available_options, usage=usage, epilog=epilog)
     
    command_options, args = parser.parse_args()
    if not args:
        parser.error('no command given, use the -h option for a list of available commands')
        
    command_name, command_args = args[0].lower(), args[1:]

    cc = CommandController()
    try:
        cc.run_command(command_name, command_options, command_args)
    except CommandError, ex:
        parser.error(ex)
    
