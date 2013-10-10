# -*- coding: utf-8 -*-
"""
Description: frontend UI

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""
#from __future__ import division
from os import path
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

class FrontendApp(WSGIApp):

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
        Mark an entry
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
        groups = get_groups(user)
    
        r = Entry.select(Entry.id).join(Read).where((Read.user == user)).naive()
        s = Entry.select(Entry.id).join(Saved).where((Saved.user == user)).naive()
        read_ids = [i.id for i in r]
        saved_ids = [i.id for i in s]
        
        if 'saved' in request.GET:
            q = get_saved_entries(user)
            panel_title = 'Starred Items'
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
        else:
            q = get_unread_entries(user)
            panel_title = 'Unread Items'
            filter_class = filter_name = 'unread'

        if 'offset' in request.GET:            
            offset = int(request.GET['offset'])
            
        entry_count = q.count()
        entries = q.order_by(Entry.last_updated_on.desc()).offset(offset).limit(ENTRIES_PER_PAGE)    

        if offset:
            templatename = '_entries_more.html'            
        else:
            templatename = 'entries.html'            
            
        offset += ENTRIES_PER_PAGE

        return self.respond_with_template(templatename, locals())


    # Feeds

    @GET(r'^/feeds/?$')
    def feed_list(self, request):
        '''
        Show subscribed feeds for current user
        '''

        # Defaults 
        offset, group_id, filter_class, panel_title = 0, 0, 'feeds', 'All Feeds' 

        user = self.get_session_user()  
        groups = get_groups(user)  

        if 'offset' in request.GET:            
            offset = int(request.GET['offset'])

        q = get_feeds(user)
        feed_count = q.count()        
        feeds = q.order_by(Feed.last_updated_on.desc()).offset(offset).limit(ENTRIES_PER_PAGE)

        if offset:
            templatename = '_feeds_more.html'            
        else:
            templatename = 'feeds.html'            
            
        offset += ENTRIES_PER_PAGE
        
        return self.respond_with_template(templatename, locals())  


    @GET(r'^/feeds/(\d+)$')
    def feed(self, request, feed_id):
        '''
        Show entries for the given feed
        '''

        user = self.get_session_user()
        feed = Feed.get(Feed.id == feed_id) 
        q = get_feed_entries(user, feed)        
        entry_count = q.count()
        
        return self.respond_with_template('_feed.html', locals())   

    @POST(r'^/ajax/feeds/add$')
    def feed_put(self, request): #@@TODO: Use PUT verb?
        '''
        Add a new feed to database
        '''

        self_link = request.POST['self_link']
        if not self_link:
            #@@TODO Check if well-formed is_valid_url(self_link)
            message = u'ERROR Please specify a valid web address'
            return self.respond_with_template('_feed_added.html', locals())
                        
        user = self.get_session_user()
        default_group = Group.get(Group.title==Group.DEFAULT_GROUP)
    
        with transaction():    
            feed = fetcher.add_feed(self_link, fetch_icon=True)    
            #@@TODO: use feed.add_subscription
            try:
                Subscription.create(user=user, feed=feed, group=default_group)
                log.debug('added feed %s for user %s' % (self_link, user.username))            
                #message = render_message(u'SUCCESS Feed %s added successfully.' % self_link)
                message = u'SUCCESS Feed %s added successfully.' % self_link

            except IntegrityError:
                log.debug('user %s has already feed %s in her subscriptions' % (user.username, self_link))    
                message = u'INFO Feed %s is already in your subscriptions.' % self_link
    
        return self.respond_with_template('_feed_added.html', locals())
    
    


        
    @GET(r'^/fever/?$')
    def fever(self, request):        
        '''
        Human readable placeholder for Fever API entry point
        '''
        return self.respond_with_template('fever.html')

    @GET(r'^/guide/?$')
    def guide(self, request):        
        return self.respond_with_template('guide.html')

    @GET(r'^/about/?$')
    def about(self, request):        
        return self.respond_with_template('about.html')


    # Template

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

    # Session user and auth

#     @property()
#     def _set_session(self, environ, session_key):
#         self.session = self.environ[session_key].session

    def get_session_user(self):                    
        '''
        Grab current session user if any or redirect to login form
        '''
        user = self.session.get('coldsweat.user', None)
        if user:
            return user
        
        raise self.redirect('%s/login?from=%s' % (self.request.application_url, escape_url(self.request.path)))
        #raise self.redirect('login?from=%s' % escape_url(self.request.path))


    @GET(r'^/login/?$')
    def login(self, request):
        d = dict(
            username = '',
            password = '',
            from_url = request.GET.get('from', '/')
        )
        
        d.update(get_health())
        
        return self.respond_with_template('login.html', d)

    @POST(r'^/login/?$')
    def login_post(self, request):

        username = request.POST.get('username')        
        password = request.POST.get('password')
        from_url = request.POST.get('from', '/')   
                    
        user = User.validate_credentials(username, password)
        if user:
            self.session['coldsweat.user'] = user
            #@@TODO response.remote_user = user.username
            return HTTPSeeOther(location=from_url)

        d = dict(
            username        = username,        
            password        = password,
            from_url        = from_url,        
            alert_message   = render_message('ERROR Unable to log in. Please check your username and password.')
        )
        
        d.update(get_health())

        #@@TODO: use redirect?
        #set_message(response, u'ERROR Unable to log in. Please check your username and password.')            
        #raise self.redirect(self.request.path)
        
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

def set_message(response, message):
    response.set_cookie('alert_message', message)    

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

def get_unread_entries(user):     
    q = Entry.select(Entry, Feed, Icon).join(Feed).join(Icon).switch(Feed).join(Subscription).where((Subscription.user == user) & ~(Entry.id << Read.select(Read.entry).where(Read.user == user)))
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
    return q    

# Groups

def get_groups(user):     
    q = Group.select().join(Subscription).where(Subscription.user == user).distinct().order_by(Group.title) 
    return q    


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



