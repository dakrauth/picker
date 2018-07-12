import os
from datetime import datetime
from pprint import pprint
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from dateutil.parser import parse
from dateutil.tz import gettz

from picker import models as picker
from picker.utils import datetime_now

def load_league():
    league, created = picker.League.objects.get_or_create(
        is_pickable=True,
        name='National Football League',
        abbr='nfl'
    )
    confs = {
        conf: picker.Conference.objects.get_or_create(
            name=conf,
            abbr=conf,
            league=league
        )[0]
        for conf in ['AFC', 'NFC']
    }
    divs = {
        key: picker.Division.objects.get_or_create(
            name=name,
            conference=confs[abbr]
        )[0]
        for key, (abbr, name) in {
            1: ['AFC', 'North'], 2: ['AFC', 'South'], 3: ['AFC', 'East'], 4: ['AFC', 'West'],
            5: ['NFC', 'North'], 6: ['NFC', 'South'], 7: ['NFC', 'East'], 8: ['NFC', 'West'],
        }.items()
    }
    teams = {
        abbr: picker.Team.objects.get_or_create(
            name=name,
            abbr=abbr,
            nickname=nickname,
            league=league,
            conference=confs[conf_abbr],
            division=divs[div_id],
            logo='picker/logos/{}.gif'.format(abbr.lower())
        )[0]
        for conf_abbr, name, div_id, nickname, abbr in [
            ['NFC', 'Arizona', 8, 'Cardinals', 'ARI'],
            ['NFC', 'Atlanta', 6, 'Falcons', 'ATL'],
            ['AFC', 'Baltimore', 1, 'Ravens', 'BAL'],
            ['AFC', 'Buffalo', 3, 'Bills', 'BUF'],
            ['NFC', 'Carolina', 6, 'Panthers', 'CAR'],
            ['NFC', 'Chicago', 5, 'Bears', 'CHI'],
            ['AFC', 'Cincinnati', 1, 'Bengals', 'CIN'],
            ['AFC', 'Cleveland', 1, 'Browns', 'CLE'],
            ['NFC', 'Dallas', 7, 'Cowboys', 'DAL'],
            ['AFC', 'Denver', 4, 'Broncos', 'DEN'],
            ['NFC', 'Detroit', 5, 'Lions', 'DET'],
            ['NFC', 'Green Bay', 5, 'Packers', 'GB'],
            ['AFC', 'Houston', 2, 'Texans', 'HOU'],
            ['AFC', 'Indianapolis', 2, 'Colts', 'IND'],
            ['AFC', 'Jacksonville', 2, 'Jaguars', 'JAX'],
            ['AFC', 'Kansas City', 4, 'Chiefs', 'KC'],
            ['AFC', 'Miami', 3, 'Dolphins', 'MIA'],
            ['NFC', 'Minnesota', 5, 'Vikings', 'MIN'],
            ['AFC', 'New England', 3, 'Patriots', 'NE'],
            ['NFC', 'New Orleans', 6, 'Saints', 'NO'],
            ['NFC', 'New York', 7, 'Giants', 'NYG'],
            ['AFC', 'New York', 3, 'Jets', 'NYJ'],
            ['AFC', 'Oakland', 4, 'Raiders', 'OAK'],
            ['NFC', 'Philadelphia', 7, 'Eagles', 'PHI'],
            ['AFC', 'Pittsburgh', 1, 'Steelers', 'PIT'],
            ['AFC', 'Los Angeles', 4, 'Chargers', 'LAC'],
            ['NFC', 'San Francisco', 8, '49ers', 'SF'],
            ['NFC', 'Seattle', 8, 'Seahawks', 'SEA'],
            ['NFC', 'Los Angeles', 8, 'Rams', 'LAR'],
            ['NFC', 'Tampa Bay', 6, 'Buccaneers', 'TB'],
            ['AFC', 'Tennessee', 2, 'Titans', 'TEN'],
            ['NFC', 'Washington', 7, 'Redskins', 'WSH']
        ]
    }

    return league, teams

def load_games(season):
    EST = gettz('US/Eastern')

    def get_dt(dts):
        dt = parse(dts)
        #dt = dt.astimezone(EST)
        return list(dt.timetuple())[:5]


    def new_week():
        return {'byes': [], 'games': []}

    dirname, _ = os.path.split(__file__)
    with open(os.path.join(dirname, '{}.txt'.format(season))) as fp:
        text = fp.read()

    week = new_week()
    weeks = [week]
    for line in text.splitlines():
        if line.startswith('BYES:'):
            _, tms = line.split(':')
            week['byes'] = tms.split(',')
        else:
            if len(week['games']) + (len(week['byes']) // 2) == 16:
                week = new_week()
                weeks.append(week)

            game = line.split('|')
            week['games'].append(game)

    def key_func(w):
        return w['games'][0][2]

    weeks.sort(key=key_func)
    byes_dict = {}
    games = []
    for i,w in enumerate(weeks, 1):
        byes = w.pop('byes')
        if byes:
            byes_dict[i] = byes

        for g in w['games']:
            g[2] = get_dt(g[2])
            g.insert(0, i)
            games.append(g)

    return games, byes_dict


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


class Command(BaseCommand):
    help = "Loads the demo DB"
    requires_migrations_checks = True
    requires_system_checks = False

    def handle(self, *args, **options):
        season = 2018
        league, teams = load_league()
        games, byes = load_games(season)
        league.create_season(season, games, byes)
        gs = league.game_set.get(season=2018, week=1)
        gs.opens = datetime_now()
        gs.save()
        load_users(league)
