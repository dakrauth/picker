import os
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from django.utils.module_loading import import_string
from django.core.validators import ValidationError, validate_email

import dateutil.tz
from dateutil.parser import parse as dt_parse

from .conf import get_setting


def parse_datetime(dtstr):
    dt = dt_parse(dtstr)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)

    return dt


def datetime_now():
    TZINFO = timezone.get_default_timezone()
    fake_now_str = os.environ.get('FAKE_DATETIME_NOW', get_setting('FAKE_DATETIME_NOW'))
    fake_now = parse_datetime(fake_now_str) if fake_now_str else None
    def inner(when=None):
        nonlocal fake_now
        if when:
            fake_now = parse_datetime(when)

        if fake_now:
            return fake_now
        else:
            return timezone.now()
    return inner
datetime_now = datetime_now()


def can_user_participate():
    participation_hooks = None
    def inner(pref, gs):
        nonlocal participation_hooks
        if participation_hooks is None:
            participation_hooks = [import_string(h) for h in get_setting('PARTICIPATION_HOOKS', [])]
        for hook in participation_hooks:
            if not hook(pref, gs):
                return False
        return True
    return inner
can_user_participate = can_user_participate()


def sorted_standings(items, key=None, reverse=True):
    weighted = []
    prev_place, prev_results = 1, (0, 0)
    for i, item in enumerate(sorted(items, reverse=reverse, key=key), 1):
        results = (item.correct, item.points_delta)
        item.place = prev_place if results == prev_results else i
        prev_place, prev_results = item.place, results
        weighted.append(item)

    return weighted


def get_templates(component, league=None):
    if component.startswith('@'):
        dirs = [component.replace('@', 'picker/{}/'.format(league.slug))] if league else []
        dirs.extend([
            component.replace('@', 'picker/'),
            component.replace('@', 'picker/_base/'),
        ])
        return dirs

    return component


def is_valid_email(value):
    try:
        validate_email(value)
    except ValidationError:
        return False
    else:
        return True

