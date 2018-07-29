import os
from pathlib import Path
from datetime import datetime
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand

from picker import models as picker
from picker.utils import datetime_now


def load_users(league):
    new, old = 0, 0
    if User.objects.filter(username='demo').exists():
        old += 1
    else:
        new += 1
        picker.Preference.objects.get_or_create(
            user=User.objects.create_superuser('demo', 'demo@example.com', 'demo')
        )
        print('Superuser username/password: demo/demo')


    for i in range(1, 10):
        name = 'user{}'.format(i)
        if User.objects.filter(username=name).exists():
            old += 1
        else:
            new += 1
            picker.Preference.objects.create(
                user=User.objects.create_user(
                    name,
                    '{}@example.com'.format(name),
                    password=name
                ),
            )
            print('User username/password: {}/{}'.format(name, name))

    return new, old


class Command(BaseCommand):
    help = "Loads the demo DB"
    requires_migrations_checks = True
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            '--league',
            default='tests/nfl.json',
            dest='league',
            help='File path to league import JSON',
        )

        parser.add_argument(
            '--season',
            default='tests/nfl2018.json',
            dest='season',
            help='File path to season import JSON',
        )

    def handle(self, *args, **options):
        call_command('migrate', no_input=True, interactive=False)
        call_command('import_league', options['league'])
        call_command('import_season', options['season'])

        gs = picker.GameSet.objects.order_by('-id')[0]
        league = gs.league
        league.game_set.get(season=gs.season, week=1)
        gs.opens = datetime_now()
        gs.save()

        new_old = load_users(league)
        print('Created {} new, {} old users'.format(*new_old))
