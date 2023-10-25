
import time
from flask import current_app as app
from peewee import JOIN, fn, IntegrityError
from ..models import (Entry, Feed, Group, Read, Saved, Subscription, FetchLog)



def get_groups_and_feeds(user):
    q = (Feed.select(Feed.id, Feed.enabled, Feed.self_link, Feed.alternate_link, Feed.title, Feed.icon_url, Group.id.alias('group_id'), Group.title.alias('group_title'))
         .join(Subscription)
         .join(Group)
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