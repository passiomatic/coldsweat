# -*- coding: utf-8 -*-
"""
Description: sweat utility commands
"""
from optparse import OptionParser, make_option
from os import path
from getpass import getpass

from wsgiref.simple_server import make_server
from webob.static import DirectoryApp

from coldsweat import opml, fetcher, template_dir
from coldsweat.models import *
from coldsweat.app import ExceptionMiddleware
from coldsweat.fever import fever_app
from coldsweat.frontend import frontend_app
from coldsweat.cascade import Cascade
from coldsweat.utilities import render_template

MIN_PASSWORD_LENGTH = 8

COMMANDS = {}

#log_filename = config.get('log', 'filename')

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
    cascade_app = ExceptionMiddleware(Cascade([static_app, fever_app, frontend_app]))
    
    httpd = make_server('localhost', options.port, cascade_app)
    print 'Serving on http://localhost:%s' % options.port
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print 'Interrupted by user'    
    
@command('refresh')
def command_refresh(parser, options, ags):
    '''Starts a feeds refresh procedure'''

    #@@TODO: Honor options.force
    
    counter = fetcher.fetch_feeds()    
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
    
    default_group = Group.get(Group.title == Group.DEFAULT_GROUP)    
    
    feeds = opml.add_feeds_from_file(args[0], fetch_icons=True)

    with transaction():
        for feed in feeds:         
            Subscription.create(user=user, group=default_group, feed=feed)

    print "%d feeds imported for user %s. See log file for more information" % (len(feeds), username)

    
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
    feeds = Feed.select().join(Subscription).join(User).where(User.id == user.id).distinct().naive()
    
    with open(filename, 'w') as f:
        f.write(render_template(path.join(template_dir, 'export.xml'), locals()))
        
    print "%d feeds exported for user %s" % (feeds.count(), username)

@command('setup')
def command_setup(parser, options, args):
    '''Sets up a working database'''
    username, password, password_again = options.username, '', ''

    setup()

    # Check if username is already in use
    try:
        User.get(User.username == username)
        print "Error: user %s alredy exists, please pick another username" % username     
        return 
    except User.DoesNotExist:
        pass
        
    while True:        
        password = getpass("Enter password for user %s: " % username)
        if len(password) < MIN_PASSWORD_LENGTH:
            print 'Error: password is too short, it should be at least %d characters long' % MIN_PASSWORD_LENGTH
            continue        
        password_again = getpass("Enter password (again): ")
        
        if password != password_again:
            print "Error: passwords do not match, please try again"
        else:
            break

    User.create(username=username, password=password, api_key=User.make_api_key(username, password))
    print "Setup for user %s completed." % username


def pre_command(test_connection=False):  
    #try
    connect()
    #except ...
    
    return True

def run():

    default_username, _ = User.DEFAULT_CREDENTIALS

    epilog = "Available commands are: %s" % ', '.join([name for name in COMMANDS])
    usage='%prog command [options] [args]'

    available_options = [
        make_option('-u', '--username', 
            dest='username', default=default_username, help="specifies a username (default %s)" % default_username),
        make_option('-f', '--force',
            dest='force', action='store_true', help='attempts to refresh even disabled feeds'),
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
        pre_command()
        handler(parser, options, command_args)        
    else:
        parser.error("unrecognized command %s, use the -h option for a list of available commands" % command_name)
        
