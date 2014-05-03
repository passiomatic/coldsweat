# -*- coding: utf-8 -*-
"""
Description: frontend UI

Copyright (c) 2013—2014 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
"""
from os import path
from datetime import datetime, timedelta
from webob.exc import HTTPSeeOther, HTTPNotFound, HTTPBadRequest, HTTPTemporaryRedirect
from tempita import Template #, HTMLTemplate 
from peewee import IntegrityError

from app import *
from models import *
from utilities import *
from session import SessionMiddleware
import fetcher
import filters
from coldsweat import logger, config, installation_dir, template_dir, VERSION_STRING

ENTRIES_PER_PAGE = 30
FEEDS_PER_PAGE = 60
USER_SESSION_KEY = 'FrontendApp.user'

def login_required(handler): 
    def wrapper(self, request, *args):
        if self.user:
            return handler(self, request, *args)
        else:
            raise self.redirect('%s/login?from=%s' % (request.application_url, filters.escape_url(request.url)))
    return wrapper
    

class FrontendApp(WSGIApp):

    def __init__(self):
        self.alert_message = ''
        self.app_namespace = {
            'version_string'    : VERSION_STRING,
            'static_url'        : STATIC_URL,
            'alert_message'     : '',
            'page_title'        : '',
        }
        # Install template filters
        for name in filters.__all__:
            filter = getattr(filters, name)
            self.app_namespace[filter.name] = filter

    def _mark_entry(self, user, entry, status):
        if status == 'read':
            try:
                Read.create(user=user, entry=entry)
            except IntegrityError:
                logger.debug('entry %s already marked as read, ignored' % entry.id)
                return
        elif status == 'unread':
            count = Read.delete().where((Read.user==user) & (Read.entry==entry)).execute()
            if not count:
                logger.debug('entry %s never marked as read, ignored' % entry.id)
                return
        elif status == 'saved':
            try:
                Saved.create(user=user, entry=entry)
            except IntegrityError:
                logger.debug('entry %s already saved, ignored' % entry.id)
                return
        elif status == 'unsaved':
            count = Saved.delete().where((Saved.user==user) & (Saved.entry==entry)).execute()
            if not count:
                logger.debug('entry %s never saved, ignored' % entry.id)
                return
        
        logger.debug('entry %s %s' % (entry.id, status))

    def _make_view_variables(self, user, request): 
        
        count, group_id, feed_id, filter_name, filter_class, panel_title, page_title = 0, 0, 0, '', '', '', ''
        
        groups = get_groups(user)    
        r = Entry.select(Entry.id).join(Read).where((Read.user == user)).naive()
        s = Entry.select(Entry.id).join(Saved).where((Saved.user == user)).naive()
        read_ids    = dict((i.id, None) for i in r)
        saved_ids   = dict((i.id, None) for i in s)
        
        if 'saved' in request.GET:
            count, q = get_saved_entries(user, Entry.id).count(), get_saved_entries(user)
            panel_title = '<i class="fa fa-star"></i>&ensp;Saved'
            filter_class = filter_name = 'saved'
            page_title = 'Saved'
        elif 'group' in request.GET:
            group_id = int(request.GET['group'])    
            group = Group.get(Group.id == group_id) 
            count, q = get_group_entries(user, group, Entry.id).count(), get_group_entries(user, group)
            panel_title = '<i class="fa fa-folder-open"></i>&ensp;%s' % group.title                
            filter_name = 'group=%s' % group_id
            page_title = group.title
        elif 'feed' in request.GET:
            feed_id = int(request.GET['feed'])
            feed = Feed.get(Feed.id == feed_id) 
            count, q = get_feed_entries(user, feed, Entry.id).count(), get_feed_entries(user, feed)
            panel_title = '<i class="fa fa-rss"></i>&ensp;<span class="%s">%s</span>' % ('' if feed.is_enabled else 'status-disabled', feed.title)
            filter_class = 'feeds'
            filter_name = 'feed=%s' % feed_id
            page_title = feed.title
        elif 'all' in request.GET:
            count, q = get_all_entries(user, Entry.id).count(), get_all_entries(user)
            panel_title = '<i class="fa fa-archive"></i>&ensp;All'                
            filter_class = filter_name = 'all'
            page_title = 'All'
        else: # Default
            count, q = get_unread_entries(user, Entry.id).count(), get_unread_entries(user)
            panel_title = '<i class="fa fa-circle"></i>&ensp;Unread'
            filter_class = filter_name = 'unread'
            page_title = 'Unread'
                    
        # Cleanup namespace
        del r, s, self
        
        return q, locals()
                        
    # Views

    @GET()
    def index(self, request):
        return self.entry_list(request)

    # Entries

    @GET(r'^/entries/(\d+)$')
    @login_required        
    def entry(self, request, entry_id):
        try:
            entry = Entry.get((Entry.id == entry_id)) 
        except Entry.DoesNotExist:
            raise HTTPNotFound('No such entry %s' % entry_id)

        self._mark_entry(self.user, entry, 'read')                                

        q, namespace = self._make_view_variables(self.user, request)
        n = q.where(Entry.last_updated_on < entry.last_updated_on).order_by(Entry.last_updated_on.desc()).limit(1)

        namespace.update({
            'entry': entry,
            'page_title': entry.title,
            #'panel_title':  '<a href="?%s">%s</a>' % (namespace['filter_name'], namespace['panel_title']),
            #'previous_entries': p,
            'next_entries': n,            
            'count': 0 # Fake it

        })

        return self.respond_with_template('entry.html', namespace)   
        
    @POST(r'^/entries/(\d+)$')
    @login_required    
    def entry_post(self, request, entry_id):
        '''
        Mark an entry as read, unread, saved and unsaved
        '''
        try:
            status = request.POST['as']
        except KeyError:
            raise HTTPBadRequest('Missing parameter as=read|unread|saved|unsaved')

        try:
            entry = Entry.get((Entry.id == entry_id)) 
        except Entry.DoesNotExist:
            raise HTTPNotFound('No such entry %s' % entry_id)
    
        if 'mark' in request.POST:
            self._mark_entry(self.user, entry, status)                        


    @GET(r'^/entries/?$')
    @login_required    
    def entry_list(self, request):
        '''
        Show entries filtered and possibly paginated by: 
            unread, saved, group or feed
        '''
        q, namespace = self._make_view_variables(self.user, request)

        offset = int(request.GET.get('offset', 0))            
        entries = q.order_by(Entry.last_updated_on.desc()).offset(offset).limit(ENTRIES_PER_PAGE)
        
        namespace.update({
            'entries'   : q.order_by(Entry.last_updated_on.desc()).offset(offset).limit(ENTRIES_PER_PAGE),
            'offset'    : offset + ENTRIES_PER_PAGE,
            'prev_date' : request.GET.get('prev_date', None),
            #'count'     : count
        })
        
        return self.respond_with_template('entries.html', namespace)


    @form(r'^/entries/mark$')
    @login_required    
    def entry_list_mark(self, request):
        '''
        Mark all entries as read
        '''
        if request.method == 'GET':
            now = datetime.utcnow()          
            return self.respond_with_template('_entries_mark_all_read.html', locals())

        # Handle postback
        try:
            before = datetime.utcfromtimestamp(int(request.POST['before']))
        except (KeyError, ValueError):
            raise HTTPBadRequest('Missing parameter before=time')
        
        q = Entry.select(Entry).join(Feed).join(Subscription).where(
            (Subscription.user == self.user) &            
            # Exclude entries already marked as read
            ~(Entry.id << Read.select(Read.entry).where(Read.user == self.user)) &
            # Exclude entries fetched after the page load
            (Feed.last_checked_on < before) 
        ).distinct()
        
        with transaction():
            for entry in q:
                try:
                    Read.create(user=self.user, entry=entry)
                except IntegrityError:
                    logger.debug('entry %d already marked as read, ignored' % entry.id)
                    continue                     
        
        self.alert_message = 'SUCCESS All entries have been marked as read'
        return self.respond_with_script('_modal_done.js', {'location': '%s/entries/?unread' % request.application_url})
                                
    # Feeds

    @GET(r'^/feeds/?$')
    @login_required    
    def feed_list(self, request):
        '''
        Show subscribed feeds for current user
        '''
        offset, group_id, filter_class, panel_title, page_title = 0, 0, 'feeds', '<span><i class="fa fa-rss"></i></span>&ensp;Feeds', 'Feeds'
        
        groups = get_groups(self.user)  
        offset = int(request.GET.get('offset', 0))
        count, q = get_feeds(self.user, Feed.id).count(), get_feeds(self.user)
        feeds = q.order_by(Feed.title).offset(offset).limit(FEEDS_PER_PAGE)
        offset += FEEDS_PER_PAGE
        
        return self.respond_with_template('feeds.html', locals())  


    @form(r'^/feeds/edit/(\d+)$')
    @login_required    
    def feed(self, request, feed_id):        
        message = ''        
        try:
            feed = Feed.get(Feed.id == feed_id) 
        except Feed.DoesNotExist:
            raise HTTPNotFound('No such feed %s' % feed_id)

        if request.method == 'POST':
            unsubscribe = int(request.POST.get('unsubscribe', 0))
            enable = int(request.POST.get('enable', 0))
            if unsubscribe:
                count = Subscription.delete().where((Subscription.user == self.user) & (Subscription.feed == feed)).execute()
                self.alert_message = u'INFO You are no longer subscribed to <i>%s</i>.' % feed.title            
            if enable:
                feed.is_enabled = True
                feed.error_count = 0                
                feed.save()
                self.alert_message = u'INFO Feed <i>%s</i> is now enabled.' % feed.title            
            return self.redirect_after_post('%s/feeds/' % request.application_url)
        else:
            q = Subscription.select(Subscription, Group).join(Group).where((Subscription.user == self.user) & (Subscription.feed == feed))
            groups = [s.group for s in q]

        return self.respond_with_template('_feed_edit.html', locals())
        

    @form(r'^/feeds/add$')
    @login_required    
    def feed_add(self, request):        
        message = ''
        groups = get_groups(self.user)
        
        if request.method == 'GET':
            return self.respond_with_template('_feed_add_wizard_1.html', locals())

        # Handle postback
        self_link = request.POST['self_link'].strip()
        if not is_valid_url(self_link):
            message = u'ERROR Error, please specify a valid web address'
            return self.respond_with_template('_feed_add_wizard_1.html', locals())
        response = fetcher.fetch_url(self_link)
        if response:
            if response.status_code not in fetcher.POSITIVE_STATUS_CODES:
                message = u'ERROR Error, feed host returned: %s' % filters.status_title(response.status_code)
                return self.respond_with_template('_feed_add_wizard_1.html', locals())
        else:
            message = u'ERROR Error, a network error occured'
            return self.respond_with_template('_feed_add_wizard_1.html', locals())


        group_id = int(request.POST.get('group', 0))
        if group_id:
            group = Group.get(Group.id == group_id) 
        else:
            group = Group.get(Group.title == Group.DEFAULT_GROUP)    

        feed = Feed()
        feed.self_link = self_link
        feed = fetcher.add_feed(feed, fetch_icon=True, add_entries=True)        
        subscription = fetcher.add_subscription(feed, self.user, group)
        if subscription:
            self.alert_message = u'SUCCESS Feed has been added to <i>%s</i> group' % group.title
        else:
            self.alert_message = u'INFO Feed is already in <i>%s</i> group' % group.title
        return self.respond_with_script('_modal_done.js', {'location': '%s/?feed=%d' % (request.application_url, feed.id)}) 

        
    @GET(r'^/fever/?$')
    def fever(self, request):        
        page_title = 'Fever Endpoint'
        return self.respond_with_template('fever.html')

    @GET(r'^/guide/?$')
    def guide(self, request):        
        page_title = 'Configure Your Feed Reader'
        return self.respond_with_template('guide.html', locals())

    @GET(r'^/about/?$')
    def about(self, request):        
        page_title = 'About'
        return self.respond_with_template('about.html', locals())


    # Template methods
    
    def respond_with_modal(self, url, message, title='', button='Close', params=None):
        namespace = {
            'url': url,
            'title': title,
            'message': message,
            'params': params if params else [],
            'button_text': button
        }                    
        return self.respond_with_template('_modal_alert.html', namespace)
    
    # @@TODO: remove code duplication with respond_with_template
    def respond_with_script(self, filename, view_namespace=None):
        
        namespace = self.app_namespace.copy()
        namespace.update({
            'request'           : self.request,
            'application_url'   : self.request.application_url,
        })

        namespace.update(view_namespace or {})
        
        if 'self' in namespace:
             # Avoid passing self or Tempita will complain
            del namespace['self']

        response = Response(
            render_template(filename, namespace),
            content_type='application/javascript', charset='utf-8')

        # Pass along alert_message cookie in the case 
        #   we force a redirect within the script
        if self.alert_message:
            response.set_cookie('alert_message', self.alert_message)
                                
        return response

    def respond_with_template(self, filename, view_namespace=None, content_type='text/html'):
        
        message = self.request.cookies.get('alert_message', '')
        
        namespace = self.app_namespace.copy()
        namespace.update({
            'request'           : self.request,
            'application_url'   : self.request.application_url,
            'alert_message'     : message
        })

        namespace.update(view_namespace or {})
        
        if 'self' in namespace:
             # Avoid passing self or Tempita will complain
            del namespace['self']

        response = Response(
            render_template(filename, namespace),
            content_type=content_type, charset='utf-8')
        
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

    # Session user and auth methods

    @property
    def user(self):
        return self.session.get(USER_SESSION_KEY, None)

    @user.setter
    def user(self, user):
        self.session[USER_SESSION_KEY] = user
                
    @form(r'^/login/?$')
    def login(self, request):

        username = request.params.get('username', '')        
        password = request.params.get('password', '')
        from_url = request.params.get('from', request.application_url)   
                    
        if request.method == 'POST':
            user = User.validate_credentials(username, password)
            if user:
                self.user = user
                return self.redirect_after_post(from_url)
            else:
                self.alert_message = 'ERROR Unable to log in. Please check your username and password.'            
                return self.redirect_after_post(request.url)
        
        page_title = 'Log In'
        d = locals()
        d.update(get_stats())
                
        return self.respond_with_template('login.html', d)

    @GET(r'^/logout/?$')
    def logout(self, request):
        response = self.redirect(request.application_url)
        response.delete_cookie('_SID_')
        return response 
        



# Install session support
frontend_app = SessionMiddleware(FrontendApp())

# ------------------------------------------------------
# Template utilities
# ------------------------------------------------------        
            
#@@TODO: use utilities.render_template - see https://bitbucket.org/ianb/tempita/issue/8/htmltemplate-escapes-too-much-in-inherited
def render_template(filename, namespace):                    
    return Template.from_filename(path.join(template_dir, filename), namespace=namespace).substitute()

# ------------------------------------------------------
# Queries
# ------------------------------------------------------        
 
# Entries

def _q(*select):
    select = select or [Entry, Feed, Icon]
    q = Entry.select(*select).join(Feed).join(Icon).switch(Feed).join(Subscription)
    return q
    
def get_unread_entries(user, *select):         
    q = _q(*select).where((Subscription.user == user) &
        ~(Entry.id << Read.select(Read.entry).where(Read.user == user))).distinct()
    return q

def get_saved_entries(user, *select):   
    q = _q(*select).where((Subscription.user == user) & 
        (Entry.id << Saved.select(Saved.entry).where(Saved.user == user))).distinct()
    return q

def get_all_entries(user, *select):     
    q = _q(*select).where(Subscription.user == user).distinct()
    return q    

def get_group_entries(user, group, *select):     
    q = _q(*select).where((Subscription.user == user) & (Subscription.group == group))
    return q

def get_feed_entries(user, feed, *select):     
    #@@FIXME: remove check if user is subscribed to the feed before blindly return q?
    q = _q(*select).where((Subscription.user == user) & (Subscription.feed == feed)).distinct()
    return q

# Feeds

def get_feeds(user, *select):  
    select = select or [Feed, Icon]   
    q = Feed.select(*select).join(Icon).switch(Feed).join(Subscription).where(Subscription.user == user).distinct()
    return q    

# Groups

def get_groups(user):     
    q = Group.select().join(Subscription).where(Subscription.user == user).distinct().order_by(Group.title) 
    return q    


# Stats

def get_stats():
    '''
    Get some user-agnostic stats from Coldsweat database 
    '''
    
    now = datetime.utcnow()
    
    last_checked_on = Feed.select().aggregate(fn.Max(Feed.last_checked_on))
    if last_checked_on:
        last_checked_on = format_datetime(last_checked_on)
    else:
        last_checked_on = 'Never'

    entry_count = Entry.select().count()        
    unread_entry_count = Entry.select().where(~(Entry.id << Read.select(Read.entry))).count()
    feed_count = Feed.select().count()
    #@@TODO: count enabled feeds with at least one subscriber
    active_feed_count = Feed.select().where(Feed.is_enabled==True).count()

    return locals()



