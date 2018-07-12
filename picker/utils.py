import re
import sys
import json
import functools
from datetime import datetime
from django.db import models, connection
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.template import loader
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
import dateutil.tz
import feedparser
from .conf import get_setting

_fake_datetime_now = get_setting('FAKE_DATETIME_NOW')
if _fake_datetime_now:
    _fake_datetime_now = datetime(
        *_fake_datetime_now,
        tzinfo=dateutil.tz.gettz(settings.TIME_ZONE)
    ).astimezone(dateutil.tz.UTC)

    def datetime_now():
        return _fake_datetime_now
else:
    def datetime_now():
        return datetime.utcnow().replace(tzinfo=dateutil.tz.UTC)

json_dumps = functools.partial(json.dumps, indent=4)


def user_email_exists(email):
    try:
        User.objects.get(email=email)
    except User.DoesNotExist:
        False
    else:
        return True


def get_templates(league, component):
    if component.startswith('@'):
        league_dir = 'picker/{}/'.format(league.lower)
        return [
            component.replace('@', league_dir),
            component.replace('@', 'picker/'),
        ]

    return component


def parse_feed(url):
    feed = feedparser.parse(url)
    entries = []
    for e in feed.get('entries', []):
        dt = e.get('published_parsed')
        dt = datetime(*dt[:6]) if dt else datetime.now()
        entries.append((
            dt,
            e.get('title', '???'),
            e.get('link'),
            e.get('summary', '')
        ))

    return sorted(entries, reverse=True)


def db_execute(sql, args):
    cursor = connection.cursor()
    cursor.execute(sql, args)
    return cursor.fetchall()


def percent(num, denom):
    return 0.0 if denom == 0 else (float(num) / denom) * 100.0


def render_to_string(request, template, data=None):
    data = data or {}
    data.update(site=Site.objects.get_current())
    return loader.render_to_string(template, data, request=request)


EMAIL_PATTERN = r'''
    (
        ^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+
        (\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*  |                     # dot-atom
        ^"(
            [\001-\010\013\014\016-\037!#-\[\]-\177]   |
            \\[\001-\011\013\014\016-\177]
        )*"                                                      # quoted-string
    )
    @(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$                                # domain
'''
email_re = re.compile(EMAIL_PATTERN, re.IGNORECASE | re.VERBOSE)


def is_valid_email(value):
    return bool(email_re.search(value))


class Attr(object):

    def __init__(self, **kws):
        self.__dict__.update(kws)

    def __getitem__(self, key):
        return getattr(self, key)


def parse_schedule(league, text):
    # Week 9 ...
    # THU, NOV 1    HI PASSING  HI RUSHING  HI RECEIVING
    # San Diego 31, Kansas City 13  Rivers 220  Mathews 67  Bowe 79
    # SUN, NOV 4    TIME (ET)   TV  TICKETS LOCATION
    # Minnesota at Seattle  4:05 PM FOX 539 Available   CenturyLink Field
    # Denver at Cincinnati  1:00 PM CBS 1,132 Available Paul Brown Stadium
    # MON, NOV 5    TIME (ET)   TV  TICKETS LOCATION
    # Philadelphia at New Orleans   8:30 PM     606 Available   Mercedes-Benz Superdome

    week_days = tuple([d + ',' for d in 'MON TUE WED THU FRI SAT SUN'.split()])
    items = []
    dct = league.team_dict()
    for line in text.splitlines():
        if line.startswith('Week '):
            continue
        elif line.startswith(week_days):
            dt = line.split('\t')[0]
        elif ' at ' in line:
            teams, tm, tv = line.split('\t')[:3]
            away, home = teams.split(' at ')
            away = dct[away]
            home = dct[home]
            when = parse('%s %s' % (dt, tm))
            items.append((away, home, when, tv or 'ESPN'))

    return items
