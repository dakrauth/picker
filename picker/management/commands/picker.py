from __future__ import absolute_import
from pprint import pprint
from datetime import datetime
from optparse import make_option
from django.core.management.base import BaseCommand
from picker import models as picker

Status = picker.Game.Status

#-------------------------------------------------------------------------------
def get_date(dt):
    if dt:
        dt = datetime(*[int(i) for i in dt.split('-')])
    else:
        dt = picker.datetime_now()

    return dt.date()


#-------------------------------------------------------------------------------
def get_team_record(tm):
    return [tm] + tm.complete_record()


#-------------------------------------------------------------------------------
def concat(items):
    return '-'.join([str(i) for i in items])


#===============================================================================
class Callbacks(object):
    
    #---------------------------------------------------------------------------
    @staticmethod
    def check_schedule(league, **options):
        DOW = {'Mon': 0, 0: 'Mon', 'Thu': 3, 3: 'Thu', 'Sat': 5, 5: 'Sat', 'Sun': 6, 6: 'Sun'}

        def pretty(e):
            return '%s %d:%02d' % (DOW[e[0]], e[1], e[2])
        
        data = league.scores()
        if not data:
            print '*** Unable to retrieve data'
            return
    
        score_strip_games = {}
        eids = {}
        for game in data['games']:
            key = '%(away)s @ %(home)s' % game
            tm = [int(i) for i in game['time'].split(':')]
            if tm[0] < 12:
                tm[0] += 12
            
            score_strip_games[key] = [DOW[game['day']]] + tm
            eids[key] = game['eid']

        print 'Score strip'
        pprint(score_strip_games)

        current_week = {}
        gs = league.current_gameset
        bad = 0
        for g in gs.games:
            ko = g.kickoff
            key = '%s @ %s' % (g.away.abbr, g.home.abbr)
            actual = score_strip_games[key]
            old = [ko.weekday(), ko.hour, ko.minute]
            if actual != old:
                print '***', key, pretty(actual), '<--', pretty(old)
                bad += 1
                eid = eids[key]
                new_ko = datetime(
                    int(eid[:4]),
                    int(eid[4:6]),
                    int(eid[6:8]),
                    actual[1],
                    actual[2]
                )
                g.kickoff = new_ko
                g.save()
        print '{} incorrect'.format(bad)


    #---------------------------------------------------------------------------
    @staticmethod
    def show_records(league, **options):
        records = [get_team_record(team) for team in league.team_set.all()]
        records = sorted(records, key=lambda r: r[-3], reverse=True)
        
        mx = max([len(unicode(r[0])) for r in records])
        hdr = '%*s %8s %8s %8s %6s' % (mx, 'Team', 'Home', 'Away', 'All', league.current_season)
        print '%s\n%s' % (hdr, '-' * len(hdr))
        for record in records:
            team = record[0]
            results = record[1:]
            print '%*s %8s %8s %8s %6s' % (
                 mx,
                 team,
                 concat(results[0]),
                 concat(results[1]),
                 concat(results[2]),
                 concat(team.season_record())
            )

    #---------------------------------------------------------------------------
    @staticmethod
    def send_reminder(league, **options):
        dt = get_date(options.get('date', None))
        first_game = league.current_gameset.first_game
        if first_game.kickoff.date() == today:
            league.send_reminder_email()
            print '%s:%s' % (today, first_game)
        else:
            print '%s:N/A' % today

    #---------------------------------------------------------------------------
    @staticmethod
    def reset_pick_results(league, **options):
        league.current_gameset.pick_set.update(correct=0, wrong=0)

    #---------------------------------------------------------------------------
    @staticmethod
    def update_status(league, **options):
        league.current_gameset.update_pick_status()

    #---------------------------------------------------------------------------
    def update_results(league, **options):
        week = league.current_gameset
        if week:
            week.update_results()

    #---------------------------------------------------------------------------
    @staticmethod
    def reset_gameweek(league, **options):
        UNPLAYED = picker.Game.Status.UNPLAYED
        league.current_gameset.exclude(status=UNPLAYED).update(status=UNPLAYED)

    #---------------------------------------------------------------------------
    @staticmethod
    def reset_week(league, **options):
        fix_games()
        reset_pick_results()

    #---------------------------------------------------------------------------
    @staticmethod
    def standings(league, **options):
        wk = options.get('week')
        if wk:
            week = league.game_set.get(week=wk, season=league.current_season)
        else:
            week = league.current_gameset
        
        print '{}, Week {}, {}'.format(week.league, week.week, week.season)
        print '%5s %4s %3s %s' % ('Place', 'Correct', 'Points', 'Picker')
        for place, pick in picker.sorted_standings(
            list(week.pick_set.select_related())
        ):
            print '%5d %7d %6d %s' % (place, pick.correct, pick.points, pick.user)


#===============================================================================
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--date', default='', dest='date', help='define a relative date'),
        make_option('--league', default=None, dest='league', help='specify which league'),
        make_option('--week', default=0, type='int', dest='week', help='define a week'),
    )
    help = 'Operations: {}'.format(', '.join(sorted([d for d in dir(Callbacks) if not d[0] == '_'])))

    #---------------------------------------------------------------------------
    def handle(self, *args, **options):
        if not args:
            print self.help
            return
        
        league = picker.League.get(options.pop('league', None))
        for arg in args:
            func = getattr(Callbacks, arg, None)
            if not func:
                print 'Skipping unknown op:', arg
            else:
                func(league, **options)
