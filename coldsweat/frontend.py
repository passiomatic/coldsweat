# -*- coding: utf-8 -*-
"""
Description: frontend UI

Copyright (c) 2013—2014 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
"""
import os
from datetime import datetime, timedelta
from functools import wraps
from webob import Request, Response
from webob.exc import *
from tempita import Template
from peewee import fn, IntegrityError

from coldsweat import *
from app import *
from models import *
from controllers import *
from utilities import *
from fetcher import *

from session import SessionMiddleware

import filters

from plugins import trigger_event, load_plugins

ENTRIES_PER_PAGE    = 30
FEEDS_PER_PAGE      = 60
USER_SESSION_KEY    = 'FrontendApp.user'

def login_required(handler): 
    @wraps(handler)
    def wrapper(self, *args):
        if self.user:
            return handler(self, *args)
        else:
            raise self.redirect('%s/login?from=%s' % (self.application_url, filters.escape_url(self.request.url)))    
    return wrapper
    

class FrontendApp(WSGIApp, FeedController, UserController):

    def __init__(self):
        super(FrontendApp, self).__init__()
    
        self.alert_message = ''
        self.app_namespace = {
            'version_string'    : VERSION_STRING,
            'static_url'        : config.web.static_url,
            'alert_message'     : '',
            'page_title'        : '',
        }
        # Install template filters
        for name in filters.__all__:
            filter = getattr(filters, name)
            self.app_namespace[filter.name] = filter

    def _make_view_variables(self): 
        
        count, group_id, feed_id, filter_name, filter_class, panel_title, page_title = 0, 0, 0, '', '', '', ''
        
        groups = self.get_groups()    
        r = Entry.select(Entry.id).join(Read).where((Read.user == self.user)).naive()
        s = Entry.select(Entry.id).join(Saved).where((Saved.user == self.user)).naive()
        read_ids    = dict((i.id, None) for i in r)
        saved_ids   = dict((i.id, None) for i in s)
        
        if 'saved' in self.request.GET:
            count, q = self.get_saved_entries(Entry.id).count(), self.get_saved_entries()
            panel_title = 'Saved'
            filter_class = filter_name = 'saved'
            page_title = 'Saved'
        elif 'group' in self.request.GET:
            group_id = int(self.request.GET['group'])    
            group = Group.get(Group.id == group_id) 
            count, q = self.get_group_entries(group, Entry.id).count(), self.get_group_entries(group)
            panel_title = group.title                
            filter_name = 'group=%s' % group_id
            page_title = group.title
        elif 'feed' in self.request.GET:
            feed_id = int(self.request.GET['feed'])
            feed = Feed.get(Feed.id == feed_id) 
            count, q = self.get_feed_entries(feed, Entry.id).count(), self.get_feed_entries(feed)
            panel_title = feed.title
            filter_class = 'feeds'
            filter_name = 'feed=%s' % feed_id
            page_title = feed.title
        elif 'all' in self.request.GET:
            count, q = self.get_all_entries(Entry.id).count(), self.get_all_entries()
            panel_title = 'All'                
            filter_class = filter_name = 'all'
            page_title = 'All'
        else: # Default
            count, q = self.get_unread_entries(Entry.id).count(), self.get_unread_entries()
            panel_title = 'Unread'
            filter_class = filter_name = 'unread'
            page_title = 'Unread'
                    
        # Cleanup namespace
        del r, s, self
        
        return q, locals()
                        
    # Views

    @GET(r'^/$')
    @login_required         
    def index(self):
        return self.entry_list()

    # Entries

    @GET(r'^/entries/(\d+)$')
    @login_required        
    def entry(self, entry_id):
        try:
            entry = Entry.get((Entry.id == entry_id)) 
        except Entry.DoesNotExist:
            raise HTTPNotFound('No such entry %s' % entry_id)

        self.mark_entry(entry, 'read')                                

        q, namespace = self._make_view_variables()
        n = q.where(Entry.last_updated_on < entry.last_updated_on).order_by(Entry.last_updated_on.desc()).limit(1)

        namespace.update({
            'entry': entry,
            'page_title': entry.title,
            'next_entries': n,            
            'count': 0 # Fake it
        })

        return self.respond_with_template('entry.html', namespace)   
        
    @POST(r'^/entries/(\d+)$')
    @login_required    
    def entry_post(self, entry_id):
        '''
        Mark an entry as read, unread, saved and unsaved
        '''
        try:
            status = self.request.POST['as']
        except KeyError:
            raise HTTPBadRequest('Missing parameter as=read|unread|saved|unsaved')

        try:
            entry = Entry.get((Entry.id == entry_id)) 
        except Entry.DoesNotExist:
            raise HTTPNotFound('No such entry %s' % entry_id)
    
        if 'mark' in self.request.POST:
            self.mark_entry(entry, status)                        


    @GET(r'^/entries/?$')
    @login_required    
    def entry_list(self):
        '''
        Show entries filtered and possibly paginated by: 
            unread, saved, group or feed
        '''
        q, namespace = self._make_view_variables()

        offset = int(self.request.GET.get('offset', 0))            
        entries = q.order_by(Entry.last_updated_on.desc()).offset(offset).limit(ENTRIES_PER_PAGE)
        
        namespace.update({
            'entries'   : q.order_by(Entry.last_updated_on.desc()).offset(offset).limit(ENTRIES_PER_PAGE),
            'offset'    : offset + ENTRIES_PER_PAGE,
            'prev_date' : self.request.GET.get('prev_date', None),
            #'count'     : count
        })
        
        return self.respond_with_template('entries.html', namespace)


    @form(r'^/entries/mark$')
    @login_required    
    def entry_list_post(self):
        '''
        Mark feed|all entries as read
        '''
        feed_id = int(self.request.GET.get('feed', 0))

        if self.request.method == 'GET':
            now = datetime.utcnow()          
            return self.respond_with_template('_entries_mark_%s_read.html' % ('feed' if feed_id else 'all'), locals())

        # Handle postback
        try:
            before = datetime.utcfromtimestamp(int(self.request.POST['before']))
        except (KeyError, ValueError):
            raise HTTPBadRequest('Missing parameter before=time')
        
        if feed_id:
            try:
                feed = Feed.get((Feed.id == feed_id)) 
            except Feed.DoesNotExist:
                raise HTTPNotFound('No such feed %s' % feed_id)
            
            q = Entry.select(Entry).join(Feed).join(Subscription).where(
                (Subscription.user == self.user) &            
                # Exclude entries already marked as read
                ~(Entry.id << Read.select(Read.entry).where(Read.user == self.user)) &
                # Filter by current feed
                (Entry.feed == feed) &
                # Exclude entries fetched after the page load                
                (Feed.last_checked_on < before) 
            ).distinct()
            message = 'SUCCESS Feed has been marked as read'
            redirect_url = '%s/entries/?feed=%s' % (self.application_url, feed_id)
        else:
            q = Entry.select(Entry).join(Feed).join(Subscription).where(
                (Subscription.user == self.user) &            
                # Exclude entries already marked as read
                ~(Entry.id << Read.select(Read.entry).where(Read.user == self.user)) &
                # Exclude entries fetched after the page load
                (Feed.last_checked_on < before) 
            ).distinct()
            message = 'SUCCESS All entries have been marked as read'
            redirect_url = '%s/entries/?unread' % self.application_url
        
        #@@TODO: Use insert_many()
        with transaction():
            for entry in q:
                try:
                    Read.create(user=self.user, entry=entry)
                except IntegrityError:
                    logger.debug('entry %d already marked as read, ignored' % entry.id)
                    continue                     
        
        self.alert_message = message        
        return self.respond_with_script('_modal_done.js', {'location': redirect_url})
                                
    # Feeds

    @GET(r'^/feeds/?$')
    @login_required    
    def feed_list(self):
        '''
        Show subscribed feeds for current user
        '''
        offset, group_id, feed_id, filter_class, panel_title, page_title = 0, 0, 0, 'feeds', 'Feeds', 'Feeds'

        error_threshold = config.fetcher.error_threshold
        groups = self.get_groups()  
        offset = int(self.request.GET.get('offset', 0))
        count, q = self.get_feeds(Feed.id).count(), self.get_feeds()
        feeds = q.order_by(Feed.title).offset(offset).limit(FEEDS_PER_PAGE)
        offset += FEEDS_PER_PAGE
        
        return self.respond_with_template('feeds.html', locals())  


    @form(r'^/feeds/edit/(\d+)$')
    @login_required    
    def feed(self, feed_id):        
        form_message = ''        
        try:
            feed = Feed.get(Feed.id == feed_id) 
        except Feed.DoesNotExist:
            raise HTTPNotFound('No such feed %s' % feed_id)
        
        # Collect editable fields 
        title = feed.title

        q = Subscription.select(Subscription, Group).join(Group).where((Subscription.user == self.user) & (Subscription.feed == feed))
        groups = [s.group for s in q]
        
        if self.request.method == 'GET':
            return self.respond_with_template('_feed_edit.html', locals())

        # Handle postback
        form = self.request.POST
        
        title = form.get('title', '').strip()
        if not title:                
            form_message = u'ERROR Error, feed title cannot be empty'
            return self.respond_with_template('_feed_edit.html', locals())
        feed.title = title
        feed.save()
        self.alert_message = u'SUCCESS Changes have been saved.'
        return self.respond_with_script('_modal_done.js', {'location': '%s/feeds/' % self.application_url}) 

        
    @form(r'^/feeds/remove/(\d+)$')
    @login_required    
    def feed_remove(self, feed_id):

        try:
            feed = Feed.get(Feed.id == feed_id) 
        except Feed.DoesNotExist:
            raise HTTPNotFound('No such feed %s' % feed_id)

        if self.request.method == 'GET':
            return self.respond_with_modal('%s/feeds/remove/%d' % (self.application_url, feed.id), 
                title=u'Remove <i>%s</i> from your subscriptions?' % feed.title, button='Remove')

        # Handle postback
        Subscription.delete().where((Subscription.user == self.user) & (Subscription.feed == feed)).execute()
        self.alert_message = u'SUCCESS You are no longer subscribed to <i>%s</i>.' % feed.title  

        return self.redirect_after_post('%s/feeds/' % self.application_url)


    @form(r'^/feeds/enable/(\d+)$')
    @login_required    
    def feed_enable(self, feed_id):

        #@@TODO: Track in which view user triggers command
        
        try:
            feed = Feed.get(Feed.id == feed_id) 
        except Feed.DoesNotExist:
            raise HTTPNotFound('No such feed %s' % feed_id)

        if self.request.method == 'GET':
            return self.respond_with_modal('%s/feeds/enable/%d' % (self.application_url, feed.id), 
                title=u'Enable <i>%s</i> again?' % feed.title, 
                body='Coldsweat will attempt to fetch it again during the next feeds refresh.', 
                button='Enable')
        
        # Handle postback
        feed.is_enabled, feed.error_count  = True, 0
        feed.save()
        self.alert_message = u'SUCCESS Feed <i>%s</i> is now enabled.' % feed.title  

        return self.redirect_after_post('%s/feeds/' % self.application_url)


    @form(r'^/feeds/add$')
    @login_required    
    def feed_add(self):        
        form_message = ''
        groups = self.get_groups()

        # URL could be passed via a GET (bookmarklet) or POST 
        self_link = self.request.params.get('self_link', '').strip()
        
        if self.request.method == 'GET':
            return self.respond_with_template('_feed_add_wizard_1.html', locals())

        if not validate_url(self_link):
            form_message = u'ERROR Error, specify a valid web address'
            return self.respond_with_template('_feed_add_wizard_1.html', locals())
        response = fetch_url(self_link)
        if response:
            if response.status_code not in fetcher.POSITIVE_STATUS_CODES:
                form_message = u'ERROR Error, feed host returned: %s' % filters.status_title(response.status_code)
                return self.respond_with_template('_feed_add_wizard_1.html', locals())
        else:
            form_message = u'ERROR Error, a network error occured'
            return self.respond_with_template('_feed_add_wizard_1.html', locals())


        group_id = int(self.request.POST.get('group', 0))
        if group_id:
            group = Group.get(Group.id == group_id) 
        else:
            group = Group.get(Group.title == Group.DEFAULT_GROUP)    

        load_plugins()
        trigger_event('fetch_started')
        feed = self.add_feed_from_url(self_link, fetch_data=True)
        trigger_event('fetch_done', [feed])                
        subscription = self.add_subscription(feed, group)
        if subscription:
            self.alert_message = u'SUCCESS Feed has been added to <i>%s</i> group' % group.title
        else:
            self.alert_message = u'INFO Feed is already in <i>%s</i> group' % group.title
        return self.respond_with_script('_modal_done.js', {'location': '%s/?feed=%d' % (self.application_url, feed.id)}) 


    @GET(r'^/fever/?$')
    def fever(self):        
        page_title = 'Fever Endpoint'
        return self.respond_with_template('fever.html')

    @GET(r'^/cheatsheet/?$')
    def about(self):        
        return self.respond_with_template('_cheatsheet.html', locals())


    @form(r'^/profile/?$')
    @login_required    
    def profile(self):        
        
        form_message = ''
        user         = self.user

        # Collect editable fields 
        email        = user.email
        password     = user.password
        
        if self.request.method == 'POST':
            form = self.request.POST

            email = form.get('email', '')
            password = form.get('password', '')
            
            if User.validate_password(password):            
                user.email = email
                user.password = password
                user.save()            
                return self.respond_with_script('_modal_done.js')
            else:
                form_message = u'ERROR Error, password is too short.'
        
        return self.respond_with_template('_user_edit.html', locals())
        

    # Template methods
    
    def respond_with_modal(self, url, title='', body='', button='Close', params=None):
        namespace = {
            'url': url,
            'title': title,
            'body': body,
            'params': params if params else [],
            'button_text': button
        }                    
        return self.respond_with_template('_modal_alert.html', namespace)
    
    def respond_with_script(self, filename, view_namespace=None):
        
        response = self._respond(filename, 'application/javascript', view_namespace) 

        # Pass along alert_message cookie in the case 
        #   we force a redirect within the script
        if self.alert_message:
            response.set_cookie('alert_message', self.alert_message)
                                
        return response

    def respond_with_template(self, filename, view_namespace=None):
        
        message = self.request.cookies.get('alert_message', '')
        
        namespace = {'alert_message' : message}
        namespace.update(view_namespace or {})
        
        response = self._respond(filename, 'text/html', namespace)
        
        # Delete alert_message cookie, if any
        if message:
            response.delete_cookie('alert_message')
                                
        return response

    def _respond(self, filename, content_type, view_namespace=None):
        
        namespace = self.app_namespace.copy()
        namespace.update({
            'request'           : self.request,
            'application_url'   : self.application_url,
        })

        namespace.update(view_namespace or {})
        
        if 'self' in namespace:
             # Avoid passing self or Tempita will complain
            del namespace['self']

        response = Response(
            _render_template(filename, namespace),
            content_type=content_type, charset='utf-8')
                                        
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
    def login(self):

        form = self.request.params

        username = form.get('username', '')        
        password = form.get('password', '')
        from_url = form.get('from', self.application_url)   
                    
        if self.request.method == 'POST':
            user = User.validate_credentials(username, password)
            if user:
                self.user = user
                return self.redirect_after_post(from_url)
            else:
                self.alert_message = 'ERROR Unable to log in. Check your username and password.'            
                return self.redirect_after_post(self.request.url)
        
        page_title = 'Log In'
        d = locals()
        d.update(get_stats())
                
        return self.respond_with_template('login.html', d)

    @GET(r'^/logout/?$')
    def logout(self):
        response = self.redirect(self.application_url)
        response.delete_cookie('_SID_')
        return response 
        
    @staticmethod
    def setup():
        return SessionMiddleware(FrontendApp())

#@@TODO: Use me
def setup_app():
    return SessionMiddleware(FrontendApp())

              
#@@TODO: use utilities.render_template - see http://bit.ly/P5Hh5m
def _render_template(filename, namespace):                    
    return Template.from_filename(os.path.join(template_dir, filename), namespace=namespace).substitute()

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



