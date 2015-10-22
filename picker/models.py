# -*- coding:utf8 -*-
import re
import json
import random
from importlib import import_module
from decimal import Decimal
from datetime import datetime, timedelta, time
from dateutil import relativedelta as rd
from dateutil.parser import parse

from django.db import models
from django.conf import settings
from django.utils.functional import cached_property
from django.contrib.auth.models import User
from django.utils.module_loading import import_string

from choice_enum import ChoiceEnumeration
from django_extensions.db.fields.json import JSONField

from . import utils
from . import signals
from .conf import get_setting as picker_setting
from . import managers


GAME_DURATION = timedelta(hours=4.5)
LOGOS_DIR     = picker_setting('LOGOS_UPLOAD_DIR', 'picker/logos')
datetime_now  = utils.datetime_now


#===============================================================================
class Preference(models.Model):
    
    #===========================================================================
    class Status(ChoiceEnumeration):
        ACTIVE    = ChoiceEnumeration.Option('ACTV', 'Active', default=True)
        INACTIVE  = ChoiceEnumeration.Option('IDLE', 'Inactive')
        SUSPENDED = ChoiceEnumeration.Option('SUSP', 'Suspended')
    
    #===========================================================================
    class Autopick(ChoiceEnumeration):
        NONE        = ChoiceEnumeration.Option('NONE', 'None')
        RANDOM      = ChoiceEnumeration.Option('RAND', 'Random', default=True)
        
    league        = models.ForeignKey('League')
    favorite_team = models.ForeignKey('Team', null=True, blank=True)
    user          = models.OneToOneField(User, related_name='picker_preferences')
    status        = models.CharField(max_length=4, choices=Status.CHOICES, default=Status.DEFAULT)
    autopick      = models.CharField(max_length=4, choices=Autopick.CHOICES, default=Autopick.DEFAULT)

    objects = managers.PreferenceManager()
    
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.user.username
    
    #---------------------------------------------------------------------------
    @cached_property
    def email(self):
        return self.user.email
        
    #---------------------------------------------------------------------------
    @cached_property
    def username(self):
        return self.user.username

    #---------------------------------------------------------------------------
    @cached_property
    def is_active(self):
        return self.user.is_active and self.status == self.Status.ACTIVE
        
    #---------------------------------------------------------------------------
    @property
    def is_suspended(self):
        return self.status == self.Status.SUSPENDED

    #---------------------------------------------------------------------------
    @property
    def should_autopick(self):
        return self.autopick != self.Autopick.NONE
        
    #---------------------------------------------------------------------------
    @cached_property
    def pretty_email(self):
        return '"{}" <{}>'.format(self.username, self.email)


#-------------------------------------------------------------------------------
def new_preferences(sender, instance, created=False, **kws):
    if created:
        return
        
    if instance.is_active:
        # TODO temp default league for preference
        league = League.get(picker_setting('DEFAULT_LEAGUE', 'nfl'))
        Preference.objects.get_or_create(user=instance, league=league)
        return

    Preference.objects.filter(user=instance).update(status=Preference.Status.INACTIVE)


models.signals.post_save.connect(new_preferences, sender=User)


#===============================================================================
class League(models.Model):
    name        = models.CharField(max_length=50, unique=True)
    abbr        = models.CharField(max_length=8)
    logo        = models.ImageField(upload_to=LOGOS_DIR, blank=True, null=True)
    is_pickable = models.BooleanField(default=False)

    objects = managers.LeagueManager()
    
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.name

    #---------------------------------------------------------------------------
    @models.permalink
    def get_absolute_url(self):
        return ('picker-home', [self.lower])
    
    #---------------------------------------------------------------------------
    @models.permalink
    def picks_url(self):
        return ('picker-picks', [self.lower])

    #---------------------------------------------------------------------------
    @models.permalink
    def results_url(self):
        return ('picker-results', [self.lower])

    #---------------------------------------------------------------------------
    @models.permalink
    def roster_url(self):
        return ('picker-roster', [self.lower])

    #---------------------------------------------------------------------------
    @models.permalink
    def teams_url(self):
        return ('picker-teams', [self.lower])

    #---------------------------------------------------------------------------
    @models.permalink
    def schedule_url(self):
        return ('picker-schedule', [self.lower])

    #---------------------------------------------------------------------------
    @models.permalink
    def manage_url(self):
        return ('picker-manage', [self.lower])
    
    #---------------------------------------------------------------------------
    @cached_property
    def lower(self):
        return self.abbr.lower()
    
    #---------------------------------------------------------------------------
    def _load_league_module(self, mod_name):
        base = picker_setting('LEAGUE_MODULE_BASE', 'picker.league')
        if base:
            try:
                return import_module('{}.{}.{}'.format(base, self.lower, mod_name))
            except ImportError:
                pass
        return None
        
    #---------------------------------------------------------------------------
    @cached_property
    def scores_module(self):
        return self._load_league_module('scores')
    
    #---------------------------------------------------------------------------
    def scores(self, *args, **kws):
        mod = self.scores_module
        return mod.scores(*args, **kws) if mod else None
    
    #---------------------------------------------------------------------------
    def teams_by_conf(self):
        abbrs = self.conference_set.values('abbr', flat=True)
        confs = {abbr.lower(): [] for abbr in abbrs}
        for team in self.team_set.all():
            confs[team.conference.abbr.lower()].append(team)
            
        return confs
        
    #---------------------------------------------------------------------------
    def get_team_name_dict(self, team=None, aliases=True):
        names = {}
        teams = [team] if team else self.team_set.all()
        for team in teams:
            names[team.abbr] = team
            names[team.name] = team
            if team.nickname:
                names[team.nickname] = team
            
            if aliases:
                for a in Alias.objects.filter(team=team):
                    names[a.name] = team
            
        return names
    
    #---------------------------------------------------------------------------
    def find_team(self, name):
        names = self.get_team_name_dict()
        return names.get(name, None)
        
    #---------------------------------------------------------------------------
    def missing_team(self, items):
        teams = self.team_names_dict()
        return set([item for item in items if item not in teams])

    #---------------------------------------------------------------------------
    @cached_property
    def current_gameset(self):
        rel = datetime_now()
        try:
            return self.game_set.get(opens__lte=rel, closes__gte=rel)
        except GameSet.DoesNotExist:
            return None
    
    #---------------------------------------------------------------------------
    @cached_property
    def current_playoffs(self):
        try:
            return self.playoff_set.get(season=self.current_season)
        except Playoff.DoesNotExist:
            return None
    
    #---------------------------------------------------------------------------
    @cached_property
    def available_seasons(self):
        return self.game_set.order_by('-season').values_list(
            'season',
            flat=True
        ).distinct()

    
    #---------------------------------------------------------------------------
    @cached_property
    def current_season(self):
        year = datetime_now().year
        abbrs = 'NFL FBS FCS NAIA'.split()
        fmt = '{}_CURRENT_SEASON'.format
        return {abbr: picker_setting(fmt(abbr), year) for abbr in abbrs}.get(
            self.abbr.upper(),
            year
        )

    #---------------------------------------------------------------------------
    def season_weeks(self, season=None):
        return self.game_set.filter(season=season or self.current_season)
        
    #---------------------------------------------------------------------------
    def random_points(self):
        d = self.game_set.filter(points__gt=0).aggregate(
            stddev=models.StdDev('points'),
            avg=models.Avg('points')
        )
        avg = int(d['avg'])
        stddev = int(d['stddev'])
        return random.randint(avg - stddev, avg + stddev)

    #---------------------------------------------------------------------------
    def send_reminder_email(self):
        gs = self.current_gameset
        signals.picker_reminder.send(sender=GameSet, week=gs)

    #---------------------------------------------------------------------------
    def create_season(self, season, schedule, byes=None):
        '''
        Create all GameSet and Game entries for a season, where:
        
        *   `season` is an int (2009)
        *   `schedule` is an iterable of 6-tuples of the following format:
            (week #, away, home, datetime or datetime-tuple, TV, location)
            
            Away and home teams are referenced by abbreviation.
            
            Example:
            
                (1, u'STL', u'SEA', (2009, 9, 13, 16, 15), 'FOX', 'Qwest Field')
                
        *   `byes` is a dictionary keyed by week number with the value being a
            list of team abbreviations
            
            Example:
            
                byes = {
                 4: [u'ATL', u'PHI', u'ARI', u'CAR'],
                 5: [u'CHI', u'GB', u'NO', u'SD'],
                 ...
                }
        '''
        current_week = None
        game_set = None
        teams = self.get_team_name_dict()
        new_old = [0, 0]
        for week, away, home, dt, tv, where in schedule:
            away = teams[away]
            home = teams[home]
            dt = dt if isinstance(dt, datetime) else datetime(*dt)

            if week != current_week:
                current_week = week

                opens = dt - timedelta(days=dt.weekday() - 1)
                opens = opens.replace(hour=12, minute=0)
                closes = opens + timedelta(days=6, seconds=3600*24-1)

                game_set, is_new = self.game_set.get_or_create(
                    season=season,
                    week=week,
                    defaults={'opens': opens, 'closes': closes}
                )
                if not is_new:
                    if game_set.opens != opens or game_set.closes != closes:
                        game_set.opens = opens
                        game_set.closes = closes
                        game_set.save()

                if byes and (week in byes):
                    game_set.byes = [teams[t] for t in byes[week]]

            g, is_new = Game.objects.get_or_create(
                home=home,
                away=away,
                week=game_set,
                kickoff=dt,
                tv=tv,
                notes='Location: ' + where,
            )

            new_old[0 if is_new else 1] += 1
        return new_old

    #---------------------------------------------------------------------------
    @classmethod
    def get(cls, abbr=None):
        abbr = abbr or picker_setting('DEFAULT_LEAGUE', 'nfl')
        return League.objects.get(abbr=abbr)


#===============================================================================
class Conference(models.Model):
    name   = models.CharField(max_length=50)
    abbr   = models.CharField(max_length=8)
    league = models.ForeignKey(League)

    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.name


#===============================================================================
class Division(models.Model):
    name       = models.CharField(max_length=50)
    conference = models.ForeignKey(Conference)

    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.name


#===============================================================================
class Team(models.Model):
    '''
    Common team attributes.
    '''
    
    name       = models.CharField(max_length=50)
    abbr       = models.CharField(max_length=8, blank=True)
    nickname   = models.CharField(max_length=50)
    location   = models.CharField(max_length=100, blank=True)
    image      = models.CharField(max_length=50, blank=True)
    league     = models.ForeignKey(League)
    conference = models.ForeignKey(Conference)
    division   = models.ForeignKey(Division, blank=True, null=True)
    colors     = models.CharField(max_length=40, blank=True)
    logo       = models.ImageField(upload_to=LOGOS_DIR, blank=True, null=True)
    
    #===========================================================================
    class Meta:
        ordering = ('name',)
        
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return u'{} {}'.format(self.name, self.nickname)
    
    #---------------------------------------------------------------------------
    @models.permalink
    def get_absolute_url(self):
        return ('picker-team', [self.league.lower, self.abbr])
    
    #---------------------------------------------------------------------------
    @property
    def aliases(self):
        return ','.join(self.alias_set.values_list('name', flat=True))

    #---------------------------------------------------------------------------
    @aliases.setter
    def aliases(self, values):
        self.alias_set.all().delete()
        for value in values.split(','):
            self.alias_set.create(name=value.strip())

    #---------------------------------------------------------------------------
    def ranking(self, week):
        try:
            return Ranking.objects.get(team=self, week__week=week)
        except:
            return None
    
    #---------------------------------------------------------------------------
    @property
    def lower(self):
        return self.abbr.lower()
    
    #---------------------------------------------------------------------------
    @cached_property
    def current_ranking(self):
        gs = league.game_set.latest('kickoff')
        return self.ranking(gs.week) or {'rank': 0, 'record': '?-?'}
        
    #---------------------------------------------------------------------------
    @property
    def schedule(self):
        games = []
        for game in  Game.objects.filter(
            models.Q(home=self) | models.Q(away=self)
        ).order_by('dt'):
            games.append((game.home if game.away.id == self.id else game.away, game))
        
        return games

    #---------------------------------------------------------------------------
    def season_record(self, season=None):
        season = season or self.league.current_season
        wins, losses, ties = (0, 0, 0)
        for game in Game.objects.exclude(status=Game.Status.UNPLAYED).filter(
            models.Q(home=self) | models.Q(away=self),
            week__season=season,
        ):
            if game.winner == self:
                wins += 1
            elif game.status == Game.Status.TIE:
                ties += 1
            else:
                losses += 1
                
        return (wins, losses, ties) if ties else (wins, losses)

    #---------------------------------------------------------------------------
    def season_points(self, season=None):
        season = season or self.league.current_season
        w, l, t = self.season_record(season)
        return ((w - l) * 2) + t
        
    #---------------------------------------------------------------------------
    def __cmp__(self, other):
        return cmp(self.season_points(), other.season_points())

    #---------------------------------------------------------------------------
    @property
    def record(self):
        return self.season_record(self.league.current_season)
        
    #---------------------------------------------------------------------------
    @property
    def record_as_string(self):
        return '-'.join(str(s) for s in self.record)

    #---------------------------------------------------------------------------
    @property
    def color_options(self):
        return self.colors.split(',')
    
    #---------------------------------------------------------------------------
    @property
    def playoff(self):
        try:
            return self.playoff_set.get(season=self.current_season)
        except Playoff.DoesNotExist:
            return None
    
    #---------------------------------------------------------------------------
    def schedule(self, season=None):
        return Game.objects.select_related('week').filter(
            models.Q(away=self) | models.Q(home=self),
            week__season=season or self.league.current_season
        )
        
    #---------------------------------------------------------------------------
    def bye_week(self, season=None):
        return self.bye_set.get(season=season or self.league.current_season)

    #---------------------------------------------------------------------------
    def complete_record(self):
        home_games = [0,0,0]
        away_games = [0,0,0]

        for game_set, accum, status in (
            (self.away_game_set, away_games, Game.Status.AWAY_WIN),
            (self.home_game_set, home_games, Game.Status.HOME_WIN),
        ):
            for res in game_set.exclude(status=Game.Status.UNPLAYED).values_list(
                'status',
                flat=True
            ):
                if res == status:
                    accum[0] += 1
                elif res == Game.Status.TIE:
                    accum[2] += 1
                else:
                    accum[1] += 1

        return [home_games, away_games, [
            away_games[0] + home_games[0],
            away_games[1] + home_games[1],
            away_games[2] + home_games[2]
        ]]
    

#===============================================================================
class Alias(models.Model):
    team = models.ForeignKey(Team)
    name = models.CharField(max_length=50, unique=True)

    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.name


#===============================================================================
class GameSet(models.Model):
    league = models.ForeignKey(League, related_name='game_set')
    season = models.PositiveSmallIntegerField()
    week   = models.PositiveSmallIntegerField()
    points = models.PositiveSmallIntegerField(default=0)
    opens  = models.DateTimeField()
    closes = models.DateTimeField()
    byes   = models.ManyToManyField(Team, verbose_name='Bye Teams', related_name='bye_set')

    #===========================================================================
    class Meta:
        ordering = ('season', 'week')
    
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return u'{}:{}'.format(self.week, self.season)

    #---------------------------------------------------------------------------
    @models.permalink
    def get_absolute_url(self):
        return ('picker-game-week', [self.league.lower, str(self.season), str(self.week)])
        
    #---------------------------------------------------------------------------
    @models.permalink
    def picks_url(self):
        return ('picker-picks-week', [self.league.lower, str(self.season), str(self.week)])

    #---------------------------------------------------------------------------
    @property
    def last_game(self):
        return self.games[-1]

    #---------------------------------------------------------------------------
    @property
    def first_game(self):
        return self.games[0]
        
    #---------------------------------------------------------------------------
    @cached_property
    def kickoff(self):
        return self.first_game.kickoff

    #---------------------------------------------------------------------------
    @property
    def end_time(self):
        return self.last_game.end_time

    #---------------------------------------------------------------------------
    @property
    def in_progress(self):
        now = datetime_now()
        return now >= self.kickoff and now <= self.end_time
        
    #---------------------------------------------------------------------------
    @property
    def has_started(self):
        return datetime_now() >= self.kickoff
        
    #---------------------------------------------------------------------------
    @property
    def is_open(self):
        return datetime_now() < self.last_game.kickoff
        
    #---------------------------------------------------------------------------
    @cached_property
    def games(self):
        return tuple(self.game_set.order_by('kickoff'))
    
    #---------------------------------------------------------------------------
    @property
    def winners(self):
        winners = []
        if self.points:
            for place, item in self.weekly_results():
                if place > 1:
                    break
                winners.append(item.user)
        return winners
        
    #---------------------------------------------------------------------------
    def update_pick_status(self):
        for wp in self.pick_set.all():
            wp.update_status()
    
    #---------------------------------------------------------------------------
    def pick_for_user(self, user):
        try:
            return self.pick_set.select_related().get(user=user)
        except PickSet.DoesNotExist:
            return None
    
    #---------------------------------------------------------------------------
    def picks_kickoff(self):
        games = set(self.game_set.all())
        force_autopick = picker_setting('FOOTBALL_FORCE_AUTOPICK', True)
        Strategy = PickSet.Strategy
        for p in Preference.objects.active():
            auto = True if force_autopick else p.should_autopick
            wp = self.pick_for_user(p.user)
            if wp:
                wp.complete_picks(auto, games)
            elif can_user_participate(p, self):
                wp = self.pick_set.create(
                    user=p.user,
                    points=self.league.random_points() if auto else 0,
                    strategy=Strategy.RANDOM if auto else Strategy.USER
                )
                wp.complete_picks(auto, games)
                wp.send_confirmation(auto)
    
    #---------------------------------------------------------------------------
    def update_results(self):
        results = self.league.scores(completed=True)
        if not results:
            return False

        completed = {g['home']: g for g in results}
        if not completed:
            return None

        count = 0
        for game in self.game_set.incomplete(home__abbr__in=completed.keys()):
            result = completed.get(game.home.abbr, None)
            if result:
                winner = result['winner']
                game.winner = (
                    game.home if game.home.abbr == winner
                    else game.away if game.away.abbr == winner else None
                )
                count += 1

        if count:
            self.update_pick_status()

        return count
    
    #---------------------------------------------------------------------------
    def set_default_open_and_close(self):
        prv = rd.relativedelta(weekday=rd.TU(-1))
        nxt = rd.relativedelta(weekday=rd.TU)
        for week in self.game_set.all():
            ko = week.kickoff
            week.opens = (ko + prv).replace(hour=12, minute=0)
            week.closes = (ko + nxt).replace(hour=11, minute=59, second=59)
            week.save()
        
    #---------------------------------------------------------------------------
    def weekly_results(self):
        picks = list(self.pick_set.select_related())
        return sorted_standings(picks)


#===============================================================================
class Game(models.Model):

    #===========================================================================
    class Category(ChoiceEnumeration):
        REGULAR = ChoiceEnumeration.Option('REG', 'Regular Season', default=True)
        POST    = ChoiceEnumeration.Option('POST', 'Post Season')

    #===========================================================================
    class Status(ChoiceEnumeration):
        UNPLAYED = ChoiceEnumeration.Option('U', 'Unplayed', default=True)
        TIE      = ChoiceEnumeration.Option('T', 'Tie')
        HOME_WIN = ChoiceEnumeration.Option('H', 'Home Win')
        AWAY_WIN = ChoiceEnumeration.Option('A', 'Away Win')
    
    home     = models.ForeignKey(Team, related_name='home_game_set')
    away     = models.ForeignKey(Team, related_name='away_game_set')
    week     = models.ForeignKey(GameSet, related_name='game_set')
    kickoff  = models.DateTimeField()
    tv       = models.CharField('TV', max_length=8, blank=True)
    notes    = models.TextField(blank=True)
    category = models.CharField(max_length=4, choices=Category.CHOICES, default=Category.DEFAULT)
    status   = models.CharField(max_length=1, choices=Status.CHOICES, default=Status.DEFAULT)
    location = models.CharField(blank=True, max_length=50)
    objects  = managers.GameManager()
    
    #===========================================================================
    class Meta:
        ordering = ('kickoff', 'away')
    
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return '{} {}'.format(self.tiny_description, self.week)
        
    #---------------------------------------------------------------------------
    @property
    def has_started(self):
        return datetime_now() >= self.kickoff

    #---------------------------------------------------------------------------
    @property
    def tiny_description(self):
        return '%s @ %s' % (self.away.abbr, self.home.abbr)
        
    #---------------------------------------------------------------------------
    @property
    def short_description(self):
        return '%s @ %s' % (self.away, self.home)

    #---------------------------------------------------------------------------
    @property
    def vs_description(self):
        return '%s vs %s' % (self.away.nickname, self.home.nickname)

    #---------------------------------------------------------------------------
    @property
    def long_description(self):
        return '%s %s %s' % (self.short_description, self.week, self.kickoff)
        
    #---------------------------------------------------------------------------
    @property
    def winner(self):
        if self.status == self.Status.HOME_WIN:
            return self.home
            
        elif self.status == self.Status.AWAY_WIN:
            return self.away
            
        return None
        
    #---------------------------------------------------------------------------
    @winner.setter
    def winner(self, team):
        if team is None:
            self.status = self.Status.TIE
        elif team  == self.away:
            self.status = self.Status.AWAY_WIN
        elif team == self.home:
            self.status = self.Status.HOME_WIN
        else:
            return
            
        self.save()
    
    #---------------------------------------------------------------------------
    def auto_pick_winner(self, pick_strategy=None):
        if pick_strategy == PickSet.Strategy.HOME:
            return self.home
        elif pick_strategy == PickSet.Strategy.BEST:
            a, b = self.home.season_points(), self.away.season_points()
            return self.home if a >= b else self.away

        return random.choice((self.home, self.away))
    
    #---------------------------------------------------------------------------
    @property
    def end_time(self):
        return self.kickoff + GAME_DURATION
        
    #---------------------------------------------------------------------------
    @property
    def in_progress(self):
        now = datetime_now()
        return now >= self.kickoff and now <= self.end_time


#===============================================================================
class PickSet(models.Model):
    
    #===========================================================================
    class Strategy(ChoiceEnumeration):
        USER     = ChoiceEnumeration.Option('USER', 'User', default=True)
        RANDOM   = ChoiceEnumeration.Option('RAND', 'Random')
        HOME     = ChoiceEnumeration.Option('HOME', 'Home Team')
        BEST     = ChoiceEnumeration.Option('BEST', 'Best Record')
    
    user = models.ForeignKey(User, related_name='pick_set')
    week = models.ForeignKey(GameSet, related_name='pick_set')
    points = models.PositiveSmallIntegerField(default=0)
    correct = models.PositiveSmallIntegerField(default=0)
    wrong = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    strategy = models.CharField(max_length=4, choices=Strategy.CHOICES, default=Strategy.DEFAULT)
    
    #===========================================================================
    class Meta:
        unique_together = (('user', 'week'),)
    
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return u'%s %s %d' % (self.week, self.user, self.correct)
        
    #---------------------------------------------------------------------------
    def __cmp__(self, o):
        return -cmp(self.correct, o.correct) or cmp(self.points_delta, o.points_delta)
        
    #---------------------------------------------------------------------------
    @property
    def is_autopicked(self):
        return self.strategy != self.Strategy.USER
        
    #---------------------------------------------------------------------------
    @property
    def is_complete(self):
        return (
            False if self.points is None
            else (self.progress == len(self.week.games))
        )
        
    #---------------------------------------------------------------------------
    @property
    def progress(self):
        return self.gamepick_set.filter(winner__isnull=False).count()
        
    #---------------------------------------------------------------------------
    def update_status(self):
        picks = self.gamepick_set.all()
        self.correct = sum([1 for gp in picks if gp.is_correct])
        self.wrong = len(picks) - self.correct
        self.save()
        return self.correct
        
    #---------------------------------------------------------------------------
    @property
    def points_delta(self):
        if self.week.points == 0:
            return 0
            
        return abs(self.points - self.week.points)
    
    #---------------------------------------------------------------------------
    def send_confirmation(self, auto_pick=False):
        signals.picker_confirmation.send(
            sender=self.__class__,
            weekly_picks=self,
            auto_pick=auto_pick
        )

    #---------------------------------------------------------------------------
    def complete_picks(self, is_random=True, games=None):
        games = games or self.week.game_set.all()
        picked_games = set((gp.game for gp in self.gamepick_set.all()))
        for g in games:
            if g not in picked_games:
                w = g.auto_pick_winner(self.Strategy.RANDOM) if is_random else None
                self.gamepick_set.create(game=g, winner=w)


#===============================================================================
class GamePick(models.Model):
    game = models.ForeignKey(Game, related_name='gamepick_set')
    winner = models.ForeignKey(Team, null=True, blank=True)
    pick = models.ForeignKey(PickSet)
    
    objects = managers.GamePickManager()
    
    #===========================================================================
    class Meta:
        ordering = ('game__kickoff', 'game__away')
    
    #---------------------------------------------------------------------------
    @property
    def kickoff(self):
        return self.game.kickoff
        
    #---------------------------------------------------------------------------
    @property
    def short_description(self):
        return self.game.short_description
        
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return u'%s: %s - Game %d' % (self.pick.user, self.winner, self.game.id)
        
    #---------------------------------------------------------------------------
    @property
    def winner_abbr(self):
        return self.winner.abbr if self.winner else 'N/A'
        
    #---------------------------------------------------------------------------
    @property
    def picked_home(self):
        return self.winner == self.game.home
        
    #---------------------------------------------------------------------------
    @property
    def is_correct(self):
        winner = self.game.winner
        if winner:
            return self.winner == winner
            
        return None


#===============================================================================
class PlayoffResult(utils.Attr):
    
    #---------------------------------------------------------------------------
    def __repr__(self):
        return u'%d,%d,%s' % (self.score, self.delta, self.picks)


#===============================================================================
class Playoff(models.Model):
    league = models.ForeignKey(League)
    season  = models.PositiveSmallIntegerField()
    kickoff = models.DateTimeField()

    #---------------------------------------------------------------------------
    @cached_property
    def seeds(self):
        return [(p.seed, p.team) for p in self.playoffteam_set.all()]
    
    #---------------------------------------------------------------------------
    @property
    def picks(self):
        return PlayoffPicks.objects.filter(self.league, season=self.season)
    
    #---------------------------------------------------------------------------
    def user_picks(self, user):
        return self.playoffpicks_set.get_or_create(user=user)[0]
    
    #---------------------------------------------------------------------------
    @property
    def admin(self):
        adm, created = self.playoffpicks_set.get_or_create(
            user__isnull=True,
            defaults={'picks': {}}
        )
        return adm
    
    #---------------------------------------------------------------------------
    @property
    def scores(self):
        results = []
        teams = dict([(t.abbr, t) for t in self.playoffteam_set.all()])
        adm_tms = self.admin.teams
        pts_dct = picker_setting('NFL_PLAYOFF_SCORE')
        for pck in self.playoffpicks_set.filter(user__isnul=False):
            points, pck_res = 0, []
            for i, (a_tm, p_tm) in enumerate(zip(adm_tms, pck.teams), 1):
                if (a_tm and p_tm) and (a_tm == p_tm):
                    good = pts_dct.get(i, 1)
                else:
                    good = 0

                points += good
                pck_res.append((good, teams[pck_tm] if pck_tm else None))
            results.append((points, -abs(adm.points - p.points), pck, pck_res))

        return [
            PlayoffResult(score=score, delta=delta, picks=picks, results=res)
            for score, delta, picks, res in sorted(results, reverse=True)
        ]

    #---------------------------------------------------------------------------
    @property
    def has_started(self):
        return self.kickoff < datetime_now()


#===============================================================================
class PlayoffTeam(models.Model):
    playoff = models.ForeignKey(Playoff)
    team = models.ForeignKey(Team)
    seed = models.PositiveSmallIntegerField()

    #===========================================================================
    class Meta:
        ordering = ('seed',)


#===============================================================================
class PlayoffPicks(models.Model):
    playoff = models.ForeignKey(Playoff)
    user    = models.ForeignKey(User, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    picks   = JSONField()

    #---------------------------------------------------------------------------
    def __unicode__(self):
        return unicode(self.user) if self.user else '<admin>'
    
    #---------------------------------------------------------------------------
    @cached_property
    def season(self):
        return self.playoff.season
    
    #---------------------------------------------------------------------------
    @property
    def teams(self):
        return tuple([self.picks.get('game_%d' % i) for i in range(1, 12)])
    
    #---------------------------------------------------------------------------
    @property
    def teams_by_round(self):
        teams = self.teams
        return tuple([teams[:4], teams[4:8], teams[8:10], teams[10:]])
    
    #---------------------------------------------------------------------------
    @property
    def points(self):
        pts = self.picks.get('points', '')
        return int(pts) if pts.isdigit() else 0


#===============================================================================
class RosterStats(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, preference, league, season=None):
        self.preference = preference
        self.user = preference.user
        self.season = season
        self.league = league
        self.is_active = preference.is_active
        self.correct = 0
        self.wrong = 0
        self.points_delta = 0

        qs = self.user.pick_set.select_related().filter(
            models.Q(correct__gt=0) | models.Q(wrong__gt=0)
        )
        
        if season:
            qs = qs.filter(week__season=season)
            
        self.weeks_played = len(qs)
        for wp in qs:
            self.correct += wp.correct
            self.wrong += wp.wrong
            self.points_delta += wp.points_delta if wp.week.points else 0

    #---------------------------------------------------------------------------
    @property
    def weeks_won(self):
        return 0
        
        qs = GameSet.objects.filter(weeksummary__weekwinner__user=self.user)
        if self.season:
            qs = qs.filter(season=self.season)
            
        return list(qs.select_related())
        
    #---------------------------------------------------------------------------
    def __str__(self):
        return '%s' % self.user
    
    __repr__ = __str__
    
    #---------------------------------------------------------------------------
    @property
    def pct(self):
        return utils.percent(self.correct, self.correct + self.wrong)
    
    #---------------------------------------------------------------------------
    @property
    def avg_points_delta(self):
        if not self.weeks_played:
            return 0
            
        return float(self.points_delta) / self.weeks_played
        
    #---------------------------------------------------------------------------
    def __cmp__(self, other):
        return (
            -cmp(self.correct, other.correct)           or
             cmp(self.points_delta, other.points_delta) or
            -cmp(self.weeks_played, other.weeks_played)
        )

    #---------------------------------------------------------------------------
    @staticmethod
    def get_details(league, season=None):
        season = season or league.current_season
        prefs = Preference.objects.select_related().order_by('user__username')
        
        by_user = {
            entry[1].user: entry
            for entry in sorted_standings([RosterStats(p, league) for p in prefs])
        }

        return [
            entry + by_user[entry[1].user]
            for entry in sorted_standings([RosterStats(p, league, season) for p in prefs])
        ]


#-------------------------------------------------------------------------------
def sorted_standings(items):
    weighted = []
    prev_place, prev_results = 1, (0,0)
    for i, item in enumerate(sorted(items), 1): 
        results = (item.correct, item.points_delta)
        place = prev_place if results == prev_results else i
        prev_place, prev_results = place, results
        weighted.append((place, item))
        
    return weighted


_participation_hooks = None

#-------------------------------------------------------------------------------
def can_user_participate(pref, week):
    global _participation_hooks
    if _participation_hooks is None:
        hooks = picker_setting('PARTICIPATION_HOOKS', [])
        _participation_hooks = [import_string(hook) for hook in hooks]
    
    for hook in _participation_hooks:
        if not hook(pref, week):
            return False
    
    return True