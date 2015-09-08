from pprint import pprint
from datetime import datetime
from optparse import make_option
from django.core.management.base import BaseCommand
from picker import models as picker
from picker.league.nfl import scores

action_callbacks = {}

#-------------------------------------------------------------------------------
def register(func):
    action_callbacks[func.__name__] = func
    return func

#-------------------------------------------------------------------------------
@register
def check(league, **options):
    DOW = {'Mon': 0, 0: 'Mon', 'Thu': 3, 3: 'Thu', 'Sat': 5, 5: 'Sat', 'Sun': 6, 6: 'Sun'}

    def pretty(e):
        return '%s %d:%02d' % (DOW[e[0]], e[1], e[2])
        
    data = scores.score_strip()
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
    gw = league.current_week
    for g in gw.games:
        ko = g.kickoff
        key = '%s @ %s' % (g.away.abbr, g.home.abbr)
        actual = score_strip_games[key]
        old = [ko.weekday(), ko.hour, ko.minute]
        if actual != old:
            print '***', key, pretty(actual), '<--', pretty(old)
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


#-------------------------------------------------------------------------------
@register
def show_records(league, **options):

    def get_record(t):
        home_games = [0,0,0]
        away_games = [0,0,0]

        for game_set, accum, status in (
            (t.away_game_set, away_games, picker.Game.AWAY_WIN_STATUS),
            (t.home_game_set, home_games, picker.Game.HOME_WIN_STATUS),
        ):
            for game in game_set.all():
                if game.status == picker.Game.UNPLAYED_STATUS:
                    continue
                elif game.status == status:
                    accum[0] += 1
                elif game.status == picker.Game.TIE_STATUS:
                    accum[2] += 1
                else:
                    accum[1] += 1

        return home_games + away_games + [away_games[0] + home_games[0], away_games[1] + home_games[1], away_games[2] + home_games[2]]

    def concat(items):
        return '-'.join([str(i) for i in items])

    records = sorted(
        [
            [team] + get_record(team)
            for team in picker.Team.objects.filter(league__abbr='NFL')
        ],
        key=lambda r: r[-3],
        reverse=True
    )
    mx = max([len(r[0].name) for r in records])
    for record in records:
        team = record[0]
        results = record[1:]
        print '%*s %8s %8s %8s' % (
             mx, team, concat(results[:3]), concat(results[3:6]), concat(results[6:])
        )


#-------------------------------------------------------------------------------
@register
def reminder(league, **options):
    if 'date' in options:
        arg = [int(i) for i in options['date'].split('-')]
        today = datetime(*arg).date()
    else:
        today = datetime.now().date()
        
    gw = league.current_week
    first_game = gw.first_game
    
    if first_game.kickoff.date() == today:
        league.send_reminder_email()
        print '%s:%s' % (today, first_game)
    else:
        print '%s:N/A' % today


#-------------------------------------------------------------------------------
@register
def reset_pick_results(league, **options):
    for wp in league.current_week.pick_set.all():
        wp.correct = 0
        wp.wrong = 0
        wp.save()


#-------------------------------------------------------------------------------
@register
def update_status(league, **options):
    league.current_week.update_pick_status()


#-------------------------------------------------------------------------------
def update_results(league, **options):
    week = league.current_week
    if week:
        week.update_results()


#-------------------------------------------------------------------------------
@register
def reset_gameweek(league, **options):
    week = league.current_week
    for g in week.game_set.exclude(status='U'):
        print g, g.status
        g.status = 'U'
        g.save()


#-------------------------------------------------------------------------------
@register
def reset_week(league, **options):
    fix_games()
    reset_pick_results()


#-------------------------------------------------------------------------------
@register
def nfl_standings(league, **options):
    wk = options.get('week')
    if wk:
        week = league.game_set.get(week=wk, season=league.current_season)
    else:
        week = league.current_week
        
    print 'NFL', week
    for place, pick in picker.sorted_standings(
        list(week.pick_set.select_related())
    ):
        print '%2d %2d %2d %s' % (place, pick.correct, pick.points, pick.user)


#-------------------------------------------------------------------------------
@register
def ncaa_standings(league, **options):
    wk = options.get('week')
    if wk:
        week = picker.Week.objects.get(week=wk)
    else:
        week = picker.Week.objects.current_week()
        
    res = picker.Picks.objects.results(week)
    
    weighted = []
    prev_place, prev_results = 1, (0,0)
    
    items = picker.Picks.objects.standings(week)
    for pick in items:
        print '%2d %2d %s' % (pick.score, pick.points, pick.user)
    
    for i, item in enumerate(items, 1): 
        results = (item.score, abs(item.points - res.points))
        place = prev_place if results == prev_results else i
        prev_place, prev_results = place, results
        weighted.append((place, item))
        
    
    
    print 'NCAA', week, res.points
    for i, pick in weighted:
        print '%2d %2d %2d %s' % (i, pick.score, pick.points, pick.user)


#===============================================================================
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--date', default='', dest='date', help='define a relative date'),
        make_option('--league', default='nfl', dest='league', help='specify which league'),
        make_option('--week', default=0, type='int', dest='week', help='define a week'),
    )
    help = 'Operations: %s' % (', '.join(sorted(action_callbacks.keys())), )

    #---------------------------------------------------------------------------
    def handle(self, *args, **options):
        if not args:
            print self.help
            return
        
        league = picker.League.objects.get(abbr=options.pop('league', 'nfl'))
        for arg in args:
            if arg not in action_callbacks:
                print 'Skipping unknown op:', arg
            
            func = action_callbacks[arg]
            func(league, **options)
