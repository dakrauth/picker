import os
from pathlib import Path
from datetime import datetime
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand

from picker import models as picker
from picker.utils import datetime_now


def create_grouping(league, name):
    group = picker.PickerGrouping.objects.create(name=name)
    group.leagues.add(league)
    return group


def load_users(grouping):
    users = []
    for name in ['demo'] + ['user{}'.format(i) for i in range(1, 10)]:
        user = User.objects.create_user(
            name,
            '{}@example.com'.format(name),
            password=name
        )
        users.append(user)
        count = len(users)
        print('{} username/password: {}/{}'.format(
            'User' if count > 1 else 'Superuser',
            name,
            name
        ))

        if count == 1:
            user.is_superuser = user.is_staff = True
            user.save()

        grouping.members.create(user=user)

    return users


class Command(BaseCommand):
    help = "Loads the demo DB"
    requires_migrations_checks = True
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument('--filename', '-f', default='tests/nfl2018.json')

    def handle(self, *args, **options):
        call_command('migrate', no_input=True, interactive=False)
        call_command('import_picks', options['filename'])

        gs = picker.GameSet.objects.order_by('-id')[0]
        league = gs.league
        gs = league.gamesets.get(season=gs.season, sequence=1)
        gs.opens = datetime_now()
        gs.save()

        grouping = create_grouping(league, 'Demo Group')
        count = load_users(grouping)
        print('Created {} new users'.format(count))


