import os
from datetime import datetime
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.core.validators import ValidationError, validate_email

from dateutil.parser import parse as dt_parse

from .conf import get_setting


def parse_datetime(dtstr):
    dt = dt_parse(dtstr)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)

    return dt


class FakeableDatetime:

    def __init__(self, default=None):
        if isinstance(default, datetime):
            default = default.isoformat()

        self.faked = False
        self.default = default or ''
        self.fake_str = os.environ.get('FAKE_DATETIME_NOW', self.default)
        self.set(self.fake_str)

    @property
    def is_fake(self):
        return bool(self.faked)

    def set(self, when):
        if when:
            if when == 'reset':
                self.faked = parse_datetime(self.fake_str) if self.fake_str else False
            else:
                self.faked = when if isinstance(when, datetime) else parse_datetime(when)

        return self.faked or timezone.now()

    def __call__(self, when=None):
        return self.set(when)


datetime_now = FakeableDatetime(get_setting('FAKE_DATETIME_NOW'))


class UserParticiption:

    @cached_property
    def participation_hooks(self):
        return [import_string(h) for h in get_setting('PARTICIPATION_HOOKS', [])]

    def __call__(self, user, gs):
        return all(hook(user, gs) for hook in self.participation_hooks)


can_user_participate = UserParticiption()


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
