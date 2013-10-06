# -*- coding: utf-8 -*-
"""
Description: frontend UI

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""
from __future__ import division
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

#     def __init__(self, **kwargs):
#         pass
        
    @GET()
    def index(self, request):

        user = self.get_session_user()
 
        d = dict(
            user        = user,
            filter_name = 'unread',
            #page_title  = 'Unread Items',     
            #page_title = '%s%s' % (page_title, ' (%s)' % entry_count if entry_count else '')
            #feed_id     = 0,
            group_id    = 0,
            entry_count = 0,
            groups = Group.select().join(Subscription).where(Subscription.user == user).distinct().order_by(Group.title).naive()
        )

        return self.respond_with_template('index.html', d)


    # Ajax calls

    @POST(r'^/ajax/feeds/add$')
    def ajax_add_feed(self, request):     

        self_link = request.POST['self_link']
        if not self_link:
            #@@TODO Check if well-formed is_valid_url(self_link)
            message = u'ERROR Please specify a valid URL'
            return self.respond_with_template('_feed_added.html', locals())
                        
        user = self.get_session_user()
        default_group = Group.get(Group.title==Group.DEFAULT_GROUP)
    
        with transaction():    
            feed = fetcher.add_feed(self_link, fetch_icon=True)    
            try:
                Subscription.create(user=user, feed=feed, group=default_group)
                log.debug('added feed %s for user %s' % (self_link, user.username))            
                #message = render_message(u'SUCCESS Feed %s added successfully.' % self_link)
                message = u'SUCCESS Feed %s added successfully.' % self_link

            except IntegrityError:
                log.debug('user %s has already feed %s in her subscriptions' % (user.username, self_link))    
                message = u'INFO Feed %s is already in your subscriptions.' % self_link
    
        return self.respond_with_template('_feed_added.html', locals())

    @GET(r'^/ajax/entries/?$')
    def ajax_entry_list(self, request):
        '''
        Show entries filtered and possibly paginated by: 
            unread, saved, group or feed
        '''

        # Defaults 
        offset, group_id, feed_id, panel_title = 0, 0, 0, 'Unread Items' 
        
        user = self.get_session_user()  
    
        r = Entry.select().join(Read).where((Read.user == user)).distinct().naive()
        s = Entry.select().join(Saved).where((Saved.user == user)).distinct().naive()
        read_ids = [i.id for i in r]
        saved_ids = [i.id for i in s]
        
        if 'saved' in request.GET:
            panel_title = 'Starred Items'
            q = get_saved_entries(user)
        elif 'group' in request.GET:
            group_id = int(request.GET['group'])    
            group, q = get_group_entries(user, group_id)
            panel_title = group.title                
        elif 'feed' in request.GET:
            feed_id = int(request.GET['feed'])
            # TODO: join(Icon) to reduce number of queries
            feed, q = get_feed_entries(user, feed_id)
            panel_title = feed.title                
        else:
            q = get_unread_entries(user)

        if 'offset' in request.GET:            
            offset = int(request.GET['offset'])
            
        entry_count = q.count()
        entries = q.order_by(Entry.last_updated_on.desc()).offset(offset).limit(ENTRIES_PER_PAGE).naive()    

        if offset:
            templatename = '_panel_entries_more.html'            
        else:
            templatename = '_panel_entries.html'            
            
        offset += ENTRIES_PER_PAGE
        
        return self.respond_with_template(templatename, locals())



    @GET(r'^/ajax/feeds/?$')
    def ajax_feed_list(self, request):
        '''
        Show subscribed feeds for current user
        '''

        # Defaults 
        offset, panel_title = 0, 'All Feeds' 

        user = self.get_session_user()  

        if 'offset' in request.GET:            
            offset = int(request.GET['offset'])

        q = get_feeds(user)
        feed_count = q.count()
        
        feeds = q.order_by(Feed.last_updated_on.desc()).offset(offset).limit(ENTRIES_PER_PAGE).naive()

        if offset:
            templatename = '_panel_feeds_more.html'            
        else:
            templatename = '_panel_feeds.html'            
            
        offset += ENTRIES_PER_PAGE
        
        return self.respond_with_template(templatename, locals())  

    @GET(r'^/ajax/feeds/(\d+)$')
    def ajax_feed(self, request, feed_id):

#         try:
#             feed = Feed.get((Feed.id == feed_id)) 
#         except Feed.DoesNotExist:
#             raise HTTPNotFound('No such feed %s' % feed_id)

        user = self.get_session_user()

        
        feed, q = get_feed_entries(user, feed_id)        
        entry_count = q.count()
        
        return self.respond_with_template('_feed.html', locals())   
    
    
    @GET(r'^/ajax/entries/(\d+)$')
    def ajax_entry(self, request, entry_id):
    
        try:
            entry = Entry.get((Entry.id == entry_id)) 
        except Entry.DoesNotExist:
            raise HTTPNotFound('No such entry %s' % entry_id)
        
        return self.respond_with_template('_entry.html', locals())   
    
    @POST(r'^/ajax/entries/(\d+)$')
    def ajax_entry_post(self, request, entry_id):
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

        
    @GET(r'^/fever/?$')
    def fever(self, request):        
        '''
        Human readable placeholder for Fever API entry point
        '''
        return self.respond_with_template('fever.html', {})

    @GET(r'^/guide/?$')
    def guide(self, request):        
        return self.respond_with_template('guide.html', {})

    @GET(r'^/about/?$')
    def about(self, request):        
        return self.respond_with_template('about.html', {})


    # Template

    def respond_with_template(self, filename, namespace=None):

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
        
        #raise self.redirect('%s/login?from=%s' % (self.request.application_url, escape_url(self.request.path)))
        raise self.redirect('login?from=%s' %  escape_url(self.request.path))


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
 
def get_unread_entries(user):     
    #@@TODO: join(Icon) to reduce number of queries
    q = Entry.select().join(Feed).join(Subscription).where((Subscription.user == user) & ~(Entry.id << Read.select(Read.entry)))
    return q

def get_saved_entries(user):   
    #@@TODO: join(Icon) to reduce number of queries  
    q = Entry.select().join(Feed).join(Subscription).where((Subscription.user == user) & (Entry.id << Saved.select(Saved.entry)))
    return q

def get_group_entries(user, group_id):     
    try:
        group = Group.get((Group.id == group_id)) 
    except Group.DoesNotExist:
        raise HTTPNotFound('No such group %s' % group_id)
    #@@TODO: join(Icon) to reduce number of queries
    q = Entry.select().join(Feed).join(Subscription).where((Subscription.user == user) & (Subscription.group == group))
    return group, q

def get_feed_entries(user, feed_id):     
    try:
        feed = Feed.get((Feed.id == feed_id)) 
    except Feed.DoesNotExist:
        raise HTTPNotFound('No such feed %s' % feed_id)
    #@@TODO: join(Icon) to reduce number of queries
    q = Entry.select().join(Feed).join(Subscription).where((Subscription.user == user) & (Subscription.feed == feed))
    return feed, q
    
def get_feeds(user):     
    #@@TODO: join(Icon) to reduce number of queries
    q = Feed.select().join(Subscription).where(Subscription.user == user)
    return q    


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
        
    unread_count = Entry.select().where(~(Entry.id << Read.select(Read.entry))).naive().count()
    if not unread_count:
        unread_count = 'None'
    
    feed_count = Feed.select().count()
    active_feed_count = Feed.select().where(Feed.is_enabled==True).count()

    # Between 0.0 and 1,0 
    #a = feed_count/active_feed_count        
    
    
    health = 1.0

    return locals()



