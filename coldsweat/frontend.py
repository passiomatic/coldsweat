# -*- coding: utf-8 -*-
"""
Description: frontend UI

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""

from webob.exc import HTTPSeeOther, HTTPNotFound, HTTPBadRequest
from tempita import Template #, HTMLTemplate 

from app import *
from models import *
from session import SessionMiddleware
from utilities import *
from coldsweat import log, config, installation_dir

#SESSION_KEY = 'com.passiomatic.coldsweat.session'
TEMPLATE_DIR = os.path.join(installation_dir, 'coldsweat/templates')
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
    
#         count =  self.session.get('count', 0)
#         print count
#         self.session['count'] = count + 1
        
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
        return self.respond_with_template('fever.html', {})

    # Template utilities

    def respond_with_template(self, filename, namespace):

        site_namespace = {
            # Global objects and settings 
            'request'           : self.request,
            'static_url'        : STATIC_URL,
            'application_url'   : self.request.application_url,

            'alert_message'     : '',

            # Filters 
            'html'              : escape_html,
            'since'             : datetime_since(datetime.utcnow()),
            'epoch'             : datetime_as_epoch,            
        }

        message = self.request.cookies.get('alert_message', '')
        if message:
            namespace['alert_message'] = render_message(message)

        site_namespace.update(namespace)                                    
        response = Response(
            render_template(filename, site_namespace),
            content_type='text/html')
        
        # Delete alert_message cookie, if any
        if message:
            response.delete_cookie('alert_message')
                                
        return response

    # Session user and auth

    def get_session_user(self):                    
        #@@TODO Grab current session user
        user = User.get((User.username == 'default'))
        return user



frontend_app = SessionMiddleware(FrontendApp())

# ------------------------------------------------------
# Template utilities
# ------------------------------------------------------        

def render_message(message):
    if not message:
        return ''
        
    try: 
        klass, text = message.split(u' ', 1)
    except ValueError:
        return text
    return u'<div class="alert alert--%s">%s</div>' % (klass.lower(), text)

def render_template(filename, namespace):                    
    return Template.from_filename(os.path.join(TEMPLATE_DIR, filename), namespace=namespace).substitute()

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





