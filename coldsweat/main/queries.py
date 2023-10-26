
import time
from flask import current_app as app
from peewee import JOIN, fn, IntegrityError
from ..models import (Entry, Feed, Group, Read, Saved, Subscription, FetchLog)



def get_groups_and_feeds(user):
    group_read_subquery = (Group.select(Group.id, fn.Count(Entry.id).alias("group_read_count"))
                           .join(Subscription)
                           .join(Feed)
                           .join(Entry)
                           .join(Read)
                           .where((Subscription.user == user) & (Subscription.user == Read.user))
                           .group_by(Group.id))
    feed_read_subquery = (Feed.select(Feed.id, fn.Count(Entry.id).alias("feed_read_count"))
                          .join(Subscription)
                          .switch(Feed)
                          .join(Entry)
                          .join(Read)
                          .where((Subscription.user == user) & (Subscription.user == Read.user))
                          .group_by(Feed.id))    
    # for fsubq in feed_read_subquery:
    #     print(fsubq.id, fsubq.feed_read_count)
    q = (Feed.select(Feed, 
                     Group.id.alias('group_id'), 
                     Group.title.alias('group_title'), 
                     group_read_subquery.c.group_read_count, 
                     feed_read_subquery.c.feed_read_count)
         .join(Subscription)
         .join(Group)
         .join(group_read_subquery, JOIN.LEFT_OUTER, on=(
             group_read_subquery.c.id == Group.id))      
         .join(feed_read_subquery, JOIN.LEFT_OUTER, on=(
             feed_read_subquery.c.id == Feed.id))                  
         .where((
             Subscription.user == user)).order_by(Group.title)).objects()
    return q


def get_group_entries(user, group_id):
    q = (Entry.select()
         .join(Feed)
         .join(Subscription)
         .join(Group)
         .where((Subscription.user == user) & (Group.id == group_id)))
    return q


def get_feed_entries(user, feed_id): 
    # Force distinct for entries from feed in multiple groups
    q = (Entry.select()
         .join(Feed)
         .join(Subscription)
         .where((Subscription.user == user) & (Feed.id == feed_id))).distinct()
    return q


def get_all_entries(user):
    # Force distinct for entries from feed in multiple groups
    q = Entry.select().join(Feed).join(Subscription).where(Subscription.user == user).distinct()
    return q


def get_fetch_log():
    return FetchLog.select().order_by(FetchLog.started_on.desc()).limit(10)