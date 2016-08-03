# -*- coding: utf-8 -*-
"""
Description: sweat utility commands

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
"""
import os, sys
from optparse import OptionParser, make_option
from getpass import getpass
import readline

from wsgiref.simple_server import make_server
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
    
