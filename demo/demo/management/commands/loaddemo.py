import os
from pprint import pprint
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from picker import models as picker
from picker.utils import datetime_now


def load_users(league):
    if not User.objects.filter(username='demo').exists():
        user = User.objects.create_superuser('demo', 'demo@example.com', 'demo')
        picker.Preference.objects.get_or_create(user=user, league=league)
    for i in range(1,10):
        name = 'user{}'.format(i)
        if not User.objects.filter(username=name).exists():
            picker.Preference.objects.get_or_create(
                user=User.objects.create_user(
                    name,
                    '{}@example.com'.format(name),
                    password=name
                ),
                league=league
            )


def file_in_this_dir(name):
    return os.path.join(os.path.dirname(__file__), name)


class Command(BaseCommand):
    help = "Loads the demo DB"
    requires_migrations_checks = True
    requires_system_checks = False

    def handle(self, *args, **options):
        season = 2018
        league, teams = picker.League.import_league(file_in_this_dir('nfl.json'))
        new_old = league.import_games(season, file_in_this_dir('nfl{}.json'.format(season)))
        gs = league.game_set.get(season=2018, week=1)
        gs.opens = datetime_now()
        gs.save()
        load_users(league)
        print('Created {} new, {} old games'.format(*new_old))
