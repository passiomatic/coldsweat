
import time
from flask import current_app as app
from peewee import JOIN, fn, IntegrityError
from ..models import (Entry, Feed, Group, Read, Saved, Subscription)



def get_groups_and_feeds(user):
    q = (Feed.select(Feed.id, Feed.title, Feed.icon_url, Group.id.alias('group_id'), Group.title.alias('group_title'))
        .join(Subscription)
        .join(Group)
        .where((
            Subscription.user == user)).order_by(Group.title)).objects()
    return q