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
#TEMPLATE_DIR = os.path.join(installation_dir, 'coldsweat/templates')
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
            group_id    = 0,
            entry_count = 0,
            groups = Group.select().join(Subscription).where(Subscription.user == user).distinct().order_by(Group.title).naive(),
        )

        return self.respond_with_template('index.html', d)

    @GET(r'^/ajax/entries/?$')
    def ajax_entry_list(self, request):

        group_id = 0
        panel_title = 'Unread Items' 
            
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
            # Default is unread
            q = get_unread_entries(user)
            
        #t = int(request.GET['t'])         
            
        entry_count = q.count()
        entries = q.order_by(Entry.last_updated_on.desc()).limit(ENTRIES_PER_PAGE).naive()    
    
        return self.respond_with_template('_panel_1.html', locals())   
  
    @GET(r'^/ajax/entries/(\d+)$')
    def ajax_entry(self, request, entry_id):
    
        try:
            entry = Entry.get((Entry.id == entry_id)) 
        except Entry.DoesNotExist:
            raise HTTPNotFound('No such entry %s' % entry_id)
        
        return self.respond_with_template('_entry.html', locals())   
    
    @POST(r'^/ajax/entries/(\d+)$')
    def ajax_entry_post(self, request, entry_id):
    
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
        # Human readable placeholder for Fever API 
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
        



# Install session support too
frontend_app = SessionMiddleware(FrontendApp())
#frontend_app = FrontendApp()

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
    #@@TODO: user
    q = Entry.select().join(Feed).join(Icon).where(~(Entry.id << Read.select(Read.entry)))
    return q

def get_saved_entries(user):     
    q = Entry.select().join(Feed).join(Icon).where((Entry.id << Saved.select(Saved.entry)))
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





