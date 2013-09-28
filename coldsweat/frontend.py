# -*- coding: utf-8 -*-
"""
Description: frontend UI

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""
from os import path
from webob.exc import HTTPSeeOther, HTTPNotFound, HTTPBadRequest, HTTPTemporaryRedirect
from tempita import Template #, HTMLTemplate 

from app import *
from models import *
from session import SessionMiddleware
from utilities import *
from coldsweat import log, config, installation_dir, template_dir

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

    @POST(r'^/feeds/add$')
    def add_feed(self, request):     

        # Redirect
        #response = HTTPSeeOther(location=ctx.request.url)
        
        self_link = request.POST['self_link']

        user = self.get_session_user()
                        
        default_group = Group.get(Group.title==Group.DEFAULT_GROUP)
    
        with transaction():    
            feed = fetcher.add_feed(self_link, fetch_icon=True)    
            try:
                Subscription.create(user=user, feed=feed, group=default_group)
                set_message(response, u'SUCCESS Feed %s added successfully.' % self_link)            
                log.debug('added feed %s for user %s' % (self_link, username))            
            except IntegrityError:
                set_message(response, u'INFO Feed %s is already in your subscriptions.' % self_link)
                log.debug('user %s has already feed %s in her subscriptions' % (username, self_link))    
    
        raise self.redirect('?feed?id=%s' % feed.id)


    # Ajax calls

    @GET(r'^/ajax/entries/?$')
    def ajax_entry_list(self, request):
        '''
        Show entries filtered and possibly paginated by: 
            unread, saved, group or feed
        '''

        # Defaults 
        page_id, group_id, feed_id, panel_title = 0, 0, 0, 'Unread Items' 
        
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

        if 'page' in request.GET:            
            page_id = int(request.GET['page'])         
            
        entry_count = q.count()
        if page_id:
            entries = q.order_by(Entry.last_updated_on.desc()).paginate(page_id, ENTRIES_PER_PAGE).naive()    
            templatename = '_panel_entries_more.html'            
        else:
            entries = q.order_by(Entry.last_updated_on.desc()).limit(ENTRIES_PER_PAGE).naive()    
            templatename = '_panel_entries.html'            

        return self.respond_with_template(templatename, locals())



    @GET(r'^/ajax/feeds/?$')
    def ajax_feed_list(self, request):
        '''
        Show subscribed feeds for current user
        '''

        # Defaults 
        t, panel_title = 0, 'All Feeds' 

        user = self.get_session_user()  

        if 't' in request.GET:            
            t = int(request.GET['t']) 

        q = get_feeds(user)
        feed_count = q.count()
        
        feeds = q.order_by(Feed.last_updated_on.desc()).limit(ENTRIES_PER_PAGE).naive()
        
        return self.respond_with_template('_panel_feeds.html', locals())  

    @GET(r'^/ajax/feeds/(\d+)$')
    def ajax_feed(self, request, feed_id):

        try:
            feed = Feed.get((Feed.id == feed_id)) 
        except Feed.DoesNotExist:
            raise HTTPNotFound('No such feed %s' % feed_id)
        
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
                    log.debug('entry %d never marked as read, ignored' % entry_id)
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
                    log.debug('entry %d never marked as saved, ignored' % entry_id)
                    return
            
            log.debug('marked entry %s as %s' % (entry_id, status))

        
    @GET(r'^/fever/?$')
    def fever(self, request):        
        '''
        Human readable placeholder for Fever API entry point
        '''
        return self.respond_with_template('fever.html', {})



    # Template

    def respond_with_template(self, filename, namespace=None):

        site_namespace = {
            # Global objects and settings 
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





