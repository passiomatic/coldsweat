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

from fever import FeverApp
from frontend import FrontendApp
import cascade

from utilities import render_template
from plugins import trigger_event, load_plugins
from markup import opml


COMMANDS = {}

def command(name):        
    '''
    Decorator to define a command
    '''
    def _(handler):
        COMMANDS[name] = handler
        return handler                
    return _
    
# ---------------------------------
# Commands 
# ---------------------------------

# @command('help')
# def command_help(parser, options, args):
#     if not args:
#         parser.error("no command name given")
# 
#     handler = COMMANDS[args[0]]
#     #parser.print_usage()
#     print '%s: %s' % (args[0], handler.__doc__)

@command('serve')
def command_serve(parser, options, ags):
    '''Starts a local server'''

    static_app = DirectoryApp("static", index_page=None)
    
    # Create a cascade that looks for static files first, 
    #  then tries the other apps
    cascade_app = ExceptionMiddleware(cascade.Cascade([static_app, FeverApp.setup(), FrontendApp.setup()]))
    
    httpd = make_server('localhost', options.port, cascade_app)
    print 'Serving on http://localhost:%s' % options.port
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print 'Interrupted by user'    
    
@command('refresh')
def command_refresh(parser, options, ags):
    '''Starts a feeds refresh procedure'''

    fc = FeedController()
    fc.fetch_all_feeds()

    print 'Refresh completed. See log file for more information'

@command('import')
def command_import(parser, options, args):
    '''Imports feeds from OPML file'''

    if not args:
        parser.error("no OPML file given")

    username = options.username

    try:
        user = User.get(User.username == username)
    except User.DoesNotExist:
        parser.error("unable to find user %s. Use -u option to specify a different user" % username)

    load_plugins()
    trigger_event('fetch_started')
    feeds = opml.add_feeds_from_file(args[0], user)
    trigger_event('fetch_done', feeds)                

    print "%d feeds imported and fetched for user %s. See log file for more information." % (len(feeds), username)

    
@command('export')
def command_export(parser, options, args):
    '''Exports feeds to OPML file'''

    if not args:
        parser.error("no OPML file given")

    username = options.username

    try:
        user = User.get(User.username == username)
    except User.DoesNotExist:
        parser.error("unable to find user %s. Use -u option to specify a different user" % username)
    
    #default_group = Group.get(Group.title == Group.DEFAULT_GROUP)
    
    filename = args[0]
    
    timestamp = format_http_datetime(datetime.utcnow())
    feeds = Feed.select().join(Subscription).where(Subscription.user == user).distinct().order_by(Feed.title)
    
    with open(filename, 'w') as f:
        f.write(render_template(os.path.join(template_dir, 'export.xml'), locals()))
        
    print "%d feeds exported for user %s" % (feeds.count(), username)
    

@command('setup')
def command_setup(parser, options, args):
    '''Sets up a working database'''
    username = options.username

    setup_database_schema()

    # Check if username is already in use
    try:
        User.get(User.username == username)
        print "Error: user %s already exists, please select another username with the -u option" % username     
        return 
    except User.DoesNotExist:
        pass

    email = raw_input("Enter e-mail for user %s (hit enter to leave blank): " % username)
        
    while True:        
        password = getpass("Enter password for user %s: " % username)
        if not User.validate_password(password):
            print 'Error: password should be at least %d characters long' % User.MIN_PASSWORD_LENGTH
            continue        
        password_again = getpass("Enter password (again): ")
        
        if password != password_again:
            print "Error: passwords do not match, please try again"
        else:
            break

    User.create(username=username, email=email, password=password)
    print "Setup for user %s completed." % username


@command('update')
def command_update(parser, options, args):
    '''Update Coldsweat internals from a previous version'''

    try:
        if migrate_database_schema():
            print 'Update completed.'
        else:
            print 'Database is already up-to-date.'
    except OperationalError, ex:         
        logger.error('caught exception updating database schema: (%s)' % ex)
        print  'Error while running database update. See log file for more information.'


def run():

    default_username, _ = User.DEFAULT_CREDENTIALS

    epilog = "Available commands are: %s" % ', '.join(sorted([name for name in COMMANDS]))
    usage='%prog command [options] [args]'

    available_options = [
        make_option('-u', '--username', 
            dest='username', default=default_username, help="specifies a username (default is %s)" % default_username),
#         make_option('-f', '--force',
#             dest='force', action='store_true', help='attempts to refresh even disabled feeds'),
        make_option('-p', '--port', default='8080', 
            dest='port', type='int', help='the port to serve on (default 8080)'),
#         make_option('-v', '--verbose',
#             dest='verbose', action='store_true', help=''),
    ]
        
    parser = OptionParser(option_list=available_options, usage=usage, epilog=epilog)
 
    options, args = parser.parse_args()
    if not args:
        parser.error('no command given, use the -h option for a list of available commands')
        
    command_name, command_args = args[0].lower(), args[1:]
    
    if command_name in COMMANDS:
        handler = COMMANDS[command_name]
        connect()
        handler(parser, options, command_args)        
    else:
        parser.error("unrecognized command %s, use the -h option for a list of available commands" % command_name)        
