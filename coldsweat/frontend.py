# -*- coding: utf-8 -*-
"""
Description: frontend UI

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""
#from __future__ import division
from os import path
from datetime import datetime, timedelta
from webob.exc import HTTPSeeOther, HTTPNotFound, HTTPBadRequest, HTTPTemporaryRedirect
from tempita import Template #, HTMLTemplate 

from app import *
from models import *
from session import SessionMiddleware
from utilities import *
from coldsweat import log, config, installation_dir, template_dir, VERSION_STRING
import fetcher

#SESSION_KEY = 'com.passiomatic.coldsweat.session'
ENTRIES_PER_PAGE = 30
USER_SESSION_KEY = 'coldsweat.user'
#RECENTLY_READ_DELTA = 5*60 # 5 minutes

class FrontendApp(WSGIApp):

    def __init__(self):
        self.alert_message = ''
    
    # Home

    @GET()
    def index(self, request):
        return self.entry_list(request)

    # Entries

    @GET(r'^/entries/(\d+)$')
    def entry(self, request, entry_id):
    
        try:
            entry = Entry.get((Entry.id == entry_id)) 
        except Entry.DoesNotExist:
            raise HTTPNotFound('No such entry %s' % entry_id)
        
        return self.respond_with_template('_entry.html', locals())   
    
    @POST(r'^/entries/(\d+)$')
    def entry_post(self, request, entry_id):
        '''
        Mark an entry as read|unread|saved|unsaved
        '''
    
        try:
            status = request.POST['as']
        except KeyError:
            raise HTTPBadRequest('Missing parameter as=read|unread|saved|unsaved')
    
        try:
            entry = Entry.get((Entry.id == entry_id)) 
        except Entry.DoesNotExist:
            raise HTTPNotFound('No such entry %s' % entry_id)
    
        user = self.get_session_user()  
        
        if 'mark' in request.POST:
            if status == 'read':
                try:
                    Read.create(user=user, entry=entry)
                except IntegrityError:
                    log.debug('entry %s already marked as read, ignored' % entry_id)
                    return
            elif status == 'unread':
                count = Read.delete().where((Read.user==user) & (Read.entry==entry)).execute()
                if not count:
                    log.debug('entry %s never marked as read, ignored' % entry_id)
                    return
            elif status == 'saved':
                try:
                    Saved.create(user=user, entry=entry)
                except IntegrityError:
                    log.debug('entry %s already marked as saved, ignored' % entry_id)
                    return
        
            elif status == 'unsaved':
                count = Saved.delete().where((Saved.user==user) & (Saved.entry==entry)).execute()
                if not count:
                    log.debug('entry %s never marked as saved, ignored' % entry_id)
                    return
            
            log.debug('marked entry %s as %s' % (entry_id, status))
            

    @GET(r'^/entries/?$')
    def entry_list(self, request):
        '''
        Show entries filtered and possibly paginated by: 
            unread, saved, group or feed
        '''

        # Defaults 
        offset, group_id, feed_id, filter_name, filter_class, panel_title = 0, 0, 0, '', '', ''

        user = self.get_session_user()  
        group_count, groups = get_groups(user)
    
        r = Entry.select(Entry.id).join(Read).where((Read.user == user)).naive()
        s = Entry.select(Entry.id).join(Saved).where((Saved.user == user)).naive()
        read_ids = [i.id for i in r]
        saved_ids = [i.id for i in s]
        
        if 'saved' in request.GET:
            q = get_saved_entries(user)
            panel_title = 'Saved Entries'
            filter_class = filter_name = 'saved'
        elif 'group' in request.GET:
            group_id = int(request.GET['group'])    
            group = Group.get(Group.id == group_id) 
            q = get_group_entries(user, group)
            panel_title = group.title                
            filter_name = 'group=%s' % group_id
        elif 'feed' in request.GET:
            feed_id = int(request.GET['feed'])
            feed = Feed.get(Feed.id == feed_id) 
            q = get_feed_entries(user, feed)
            panel_title = feed.title                
            filter_class = 'feeds'
            filter_name = 'feed=%s' % feed_id
        elif 'all' in request.GET:
            q = get_all_entries(user)
            panel_title = 'All Entries'                
            filter_class = filter_name = 'all'
        else: # Default
            #since = now - timedelta(seconds=RECENTLY_READ_DELTA)
            q = get_unread_entries(user)
            panel_title = 'Unread Entries'
            filter_class = filter_name = 'unread'

        if 'offset' in request.GET:            
            offset = int(request.GET['offset'])
            
        entry_count, entries = q.count(), q.order_by(Entry.last_updated_on.desc()).offset(offset).limit(ENTRIES_PER_PAGE)
        offset += ENTRIES_PER_PAGE

        return self.respond_with_template('entries.html', locals())

    @GET(r'^/entries/mark$')
    def entry_list_mark(self, request):  
        now = datetime.utcnow()          
        user = self.get_session_user()      
        return self.respond_with_template('_entries_mark_all_read.html', locals())
        
    @POST(r'^/entries/mark$')
    def entry_list_mark_post(self, request):
        '''
        Mark all entries as read
        '''
        try:
            before = datetime.utcfromtimestamp(int(request.POST['before']))
        except (KeyError, ValueError):
            raise HTTPBadRequest('Missing parameter before=time')
        
        user = self.get_session_user()      
        q = Entry.select().join(Feed).join(Subscription).where(
            (Subscription.user == user) &            
            # Exclude entries already marked as read
            ~(Entry.id << Read.select(Read.entry).where(Read.user == user)) &
            # Exclude entries parsed after the page load
            (Feed.last_checked_on < before) 
        )

        with transaction():
            for entry in q:
                try:
                    Read.create(user=user, entry=entry)
                except IntegrityError:
                    log.warn('entry %s already marked as read, ignored' % entry.id)
                    continue                     

        return self.respond_with_modal(request.application_url, 
            message=render_message('SUCCESS All entries have been marked as read'), 
            params=[('unread', '')])
                                                        
    # Feeds

    @GET(r'^/feeds/?$')
    def feed_list(self, request):
        '''
        Show subscribed feeds for current user
        '''

        # Defaults 
        offset, group_id, filter_class, panel_title = 0, 0, 'feeds', 'Feeds' 

        user = self.get_session_user()  
        group_count, groups = get_groups(user)  

        if 'offset' in request.GET:            
            offset = int(request.GET['offset'])

        feed_count, feeds_q = get_feeds(user)
        feeds = feeds_q.order_by(Feed.title).offset(offset).limit(ENTRIES_PER_PAGE)
        offset += ENTRIES_PER_PAGE
        
        return self.respond_with_template('feeds.html', locals())  


    @GET(r'^/feeds/(\d+)$')
    def feed(self, request, feed_id):
        '''
        Show entries for the given feed
        '''

        user = self.get_session_user()

        try:
            feed = Feed.get(Feed.id == feed_id) 
        except Entry.DoesNotExist:
            raise HTTPNotFound('No such feed %s' % feed_id)
        
        q = get_feed_entries(user, feed)        
        entry_count = q.count()
        
        return self.respond_with_template('_feed.html', locals())   

    @GET(r'^/feeds/add$')
    def feed_add(self, request):        
        '''
        1. Show input form
        '''
        message = ''
        return self.respond_with_template('_feed_add_wizard_1.html', locals())

    @POST(r'^/feeds/add$')
    def feed_add_post(self, request):        
        '''
        2. Check, fetch and finally add the feed
        '''
        self_link = request.POST['self_link'].strip()
        if not is_valid_url(self_link):
            message = render_message(u'ERROR Error, please specify a valid web address')
            return self.respond_with_template('_feed_add_wizard_1.html', locals())
        status = fetcher.check_url(self_link)
        if status in (300, 404, 410, 500):
            message = render_message(u'ERROR Error, feed host returned status code: %s' % get_status_title(status))
            return self.respond_with_template('_feed_add_wizard_1.html', locals())

        feed = Feed()
        feed.self_link = self_link
        feed = fetcher.add_feed(feed, fetch_icon=True, add_entries=True)        
        user = self.get_session_user()        
        subscription = fetcher.add_subscription(feed, user)
        if subscription:
            message = render_message('SUCCESS Feed has been added to your subscription')
        else:
            message = render_message('INFO Feed is already in your subscriptions')

        return self.respond_with_modal(request.application_url, 
            message=message,
            button = 'View Feed Entries',
            params=[('feed', feed.id)])
                        

    @GET(r'^/shortcuts/?$')
    def shortcuts(self, request):        
        return self.respond_with_template('_shortcuts.html')

        
    @GET(r'^/fever/?$')
    def fever(self, request):        
        return self.respond_with_template('fever.html')

    @GET(r'^/guide/?$')
    def guide(self, request):        
        return self.respond_with_template('guide.html')

    @GET(r'^/about/?$')
    def about(self, request):        
        return self.respond_with_template('about.html')


    # Template
    
    def respond_with_modal(self, url, message, title='', button='Close', params=None):
        namespace = {
            'url': url,
            'title': title,
            'message': message,
            'params': params if params else [],
            'button_text': button
        }                    
        return self.respond_with_template('_modal_alert.html', namespace)
    
    def respond_with_template(self, filename, namespace=None):

        namespace = namespace or {}

        site_namespace = {
            # Global objects and settings 
            'version_string'    : VERSION_STRING,
            'request'           : self.request,
            'static_url'        : STATIC_URL,
            'application_url'   : self.request.application_url,
            'alert_message'     : '',

            # Filters 
            'html'              : escape_html,
            'url'               : escape_url,
            'since'             : datetime_since(datetime.utcnow()),
            'epoch'             : datetime_as_epoch,            
        }

        message = self.request.cookies.get('alert_message', '')
        if message:
            namespace['alert_message'] = render_message(message)

        if 'self' in namespace:
            del namespace['self'] # Avoid passing self to Tempita

        site_namespace.update(namespace or {})
        response = Response(
            render_template(filename, site_namespace),
            content_type='text/html', charset='utf-8')
        
        # Delete alert_message cookie, if any
        if message:
            response.delete_cookie('alert_message')
                                
        return response

    def _redirect(self, klass, location):
        '''
        Return a temporary or permament redirect response object. 
          Caller may return it or raise it.
        '''
        response = klass(location=location)
        if self.alert_message:
            response.set_cookie('alert_message', self.alert_message)
        return response

    def redirect(self, location):
        '''
        Return a temporary redirect response object. 
          Caller may return it or raise it.
        '''
        
        return self._redirect(HTTPTemporaryRedirect, location)

    def redirect_after_post(self, location):
        '''
        Return a 'see other' redirect response object. 
          Caller may return it or raise it.
        '''
        return self._redirect(HTTPSeeOther, location)

    # Session user and auth

#     @property()
#     def _set_session(self, environ, session_key):
#         self.session = self.environ[session_key].session

    def get_session_user(self):                    
        '''
        Grab current session user if any or redirect to login form
        '''
        user = self.session.get(USER_SESSION_KEY, None)
        if user:
            return user
        
        raise self.redirect('%s/login?from=%s' % (self.request.application_url, escape_url(self.request.url)))


    @form(r'^/login/?$')
    def login(self, request):

        username = request.params.get('username', '')        
        password = request.params.get('password', '')
        from_url = request.params.get('from', request.application_url)   
                    
        if request.method == 'POST':
            user = User.validate_credentials(username, password)
            if user:
                self.session[USER_SESSION_KEY] = user
                return self.redirect_after_post(from_url)
            else:
                self.alert_message = 'ERROR Unable to log in. Please check your username and password.'            
                return self.redirect_after_post(request.url)

        d = locals()
        d.update(get_health())
                
        return self.respond_with_template('login.html', d)

    @GET(r'^/logout/?$')
    def logout(self, request):
        response = self.redirect('/')
        response.delete_cookie('_SID_')
        return response 
        



# Install session support
frontend_app = SessionMiddleware(FrontendApp())

# ------------------------------------------------------
# Template utilities
# ------------------------------------------------------        
# 
# def set_message(response, message):
#     response.set_cookie('alert_message', message)    

def render_message(message):
    if not message:
        return ''
        
    try: 
        klass, text = message.split(u' ', 1)
    except ValueError:
        return text
    return u'<div class="alert alert--%s">%s</div>' % (klass.lower(), text)

            
#@@TODO: use utilities.render_template
def render_template(filename, namespace):                    
    return Template.from_filename(path.join(template_dir, filename), namespace=namespace).substitute()

# ------------------------------------------------------
# Queries
# ------------------------------------------------------        
 
# Entries

def get_unread_entries(user, since=None):         
    '''
    Get unread entries and optionally entries read after the given time
    '''
    if since:
        q = Entry.select(Entry, Feed, Icon).join(Feed).join(Icon).switch(Feed).join(Subscription).where((Subscription.user == user) & \
        ~(Entry.id << Read.select(Read.entry).where(Read.user == user).naive()) | \
        (Entry.id << Read.select(Read.entry).where((Read.user == user) & (Read.read_on > since)).naive()))
    else:
        q = Entry.select(Entry, Feed, Icon).join(Feed).join(Icon).switch(Feed).join(Subscription).where((Subscription.user == user) & \
            ~(Entry.id << Read.select(Read.entry).where(Read.user == user).naive()))
    return q

def get_all_entries(user):     
    q = Entry.select(Entry, Feed, Icon).join(Feed).join(Icon).switch(Feed).join(Subscription).where(Subscription.user == user)
    return q    

def get_saved_entries(user):   
    q = Entry.select(Entry, Feed, Icon).join(Feed).join(Icon).switch(Feed).join(Subscription).where((Subscription.user == user) & (Entry.id << Saved.select(Saved.entry).where(Saved.user == user)))
    return q

def get_group_entries(user, group):     
    q = Entry.select(Entry, Feed, Icon).join(Feed).join(Icon).switch(Feed).join(Subscription).where((Subscription.user == user) & (Subscription.group == group))
    return q

def get_feed_entries(user, feed):     
    q = Entry.select(Entry, Feed, Icon).join(Feed).join(Icon).switch(Feed).join(Subscription).where((Subscription.user == user) & (Subscription.feed == feed))
    return q

# Feeds

def get_feeds(user):     
    #@@TODO: Add join(Entry, JOIN_LEFT_OUTER).annotate(Entry) # No. of entries in feed
    q = Feed.select(Feed, Icon).join(Icon).switch(Feed).join(Subscription).where(Subscription.user == user)
    return q.count(), q    

# Groups

def get_groups(user):     
    q = Group.select().join(Subscription).where(Subscription.user == user).distinct().order_by(Group.title) 
    return q.count(), q    


# Stats

def get_health():
    '''
    Get some user-agnostic stats from Coldsweat database 
    '''
    
    now = datetime.utcnow()
    
    #last_entries = Entry.select().join(Feed).join(Icon).where(~(Entry.id << Read.select(Read.entry))).order_by(Entry.last_updated_on.desc()).limit(5).naive()
        
    last_checked_on = Feed.select().aggregate(fn.Max(Feed.last_checked_on))
    if last_checked_on:
        b = (now - last_checked_on).days
        last_checked_on = format_datetime(last_checked_on)
        # Between 0 and timedelta.max     
    else:
        last_checked_on = 'Never'
        b = 0 #timedelta.max.days
        
    unread_count = Entry.select().where(~(Entry.id << Read.select(Read.entry))).count()
    if not unread_count:
        unread_count = 'None'
    
    feed_count = Feed.select().count()
    active_feed_count = Feed.select().where(Feed.is_enabled==True).count()

    # Between 0.0 and 1,0 
    #a = feed_count/active_feed_count        
    
    
    health = 1.0

    return locals()



