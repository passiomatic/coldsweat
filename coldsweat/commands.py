# -*- coding: utf-8 -*-
"""
Description: sweat utility commands
"""
from optparse import OptionParser, make_option
from getpass import getpass

from coldsweat.models import *
from coldsweat import opml
from coldsweat import fetcher
#from coldsweat import config

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

@command('refresh')
def command_refresh(parser, options, ags):
    '''Starts a feeds refresh procedure'''
    
    counter = fetcher.fetch_feeds()    
    print 'Refresh completed. See log file for more information'

@command('import')
def command_import(parser, options, args):
    '''Imports feeds from a OPML file'''

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

@command('setup')
def command_setup(parser, options, args):
    '''Sets up a working database'''
    username, password, password_again = options.username, '', ''

    while True:        
        password = getpass("Enter password for user %s: " % username)
        if len(password) < MIN_PASSWORD_LENGTH:
            print 'Error: password is too short, it should be at least %d characters long' % MIN_PASSWORD_LENGTH
            continue        
        password_again = getpass("Enter password (again): ")
        
        if password != password_again:
            print "Error: passwords don't match, please try again"
        else:
            break

    setup(username, password)

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
            dest='username', default=default_username, help="specifies a username, default is %s" % default_username),
        make_option('-f', '--force',
            dest='force', action='store_true', help='attempts to refresh even disabled feeds'),
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
        
