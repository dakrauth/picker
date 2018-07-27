# -*- coding:utf8 -*-
import os
import json
import random
import functools
from importlib import import_module
from datetime import datetime, timedelta

from dateutil.tz import UTC
from dateutil import relativedelta as rd

from django.db import models
from django.urls import reverse
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from dateutil.parser import parse as parse_dt
from choice_enum import ChoiceEnumeration
from django_extensions.db.fields.json import JSONField

from .utils import Attr, datetime_now, parse_feed, percent
from . import signals
from .exceptions import PickerResultException
from .conf import get_setting as picker_setting
from . import managers

GAME_DURATION = timedelta(hours=4.5)
LOGOS_DIR = picker_setting('LOGOS_UPLOAD_DIR', 'picker/logos/nfl')




def get_dt(dts):
    dt = parse(dts)
    return list(dt.timetuple())[:5]


class Preference(models.Model):

    class Status(ChoiceEnumeration):
        ACTIVE = ChoiceEnumeration.Option('ACTV', 'Active', default=True)
        INACTIVE = ChoiceEnumeration.Option('IDLE', 'Inactive')
        SUSPENDED = ChoiceEnumeration.Option('SUSP', 'Suspended')

    class Autopick(ChoiceEnumeration):
        NONE = ChoiceEnumeration.Option('NONE', 'None')
        RANDOM = ChoiceEnumeration.Option('RAND', 'Random', default=True)

    league = models.ForeignKey('League', on_delete=models.CASCADE)
    favorite_team = models.ForeignKey('Team', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='picker_preferences'
    )
    status = models.CharField(max_length=4, choices=Status.CHOICES, default=Status.DEFAULT)
    autopick = models.CharField(max_length=4, choices=Autopick.CHOICES, default=Autopick.DEFAULT)

    objects = managers.PreferenceManager()

    class Meta:
        unique_together = ('league', 'user')

    def __str__(self):
        return '{}:{}'.format(self.user.username, self.league)

    @cached_property
    def email(self):
        return self.user.email

    @cached_property
    def username(self):
        return self.user.username

    @cached_property
    def is_active(self):
        return self.user.is_active and self.status == self.Status.ACTIVE

    @property
    def is_suspended(self):
        return self.status == self.Status.SUSPENDED

    @property
    def should_autopick(self):
        return self.autopick != self.Autopick.NONE

    @cached_property
    def pretty_email(self):
        return '"{}" <{}>'.format(self.username, self.email)


class PickerGrouping(models.Model):
    class Status(ChoiceEnumeration):
        ACTIVE = ChoiceEnumeration.Option('ACTV', 'Active', default=True)
        INACTIVE = ChoiceEnumeration.Option('IDLE', 'Inactive')

    name = models.CharField(max_length=75, unique=True)
    leagues = models.ManyToManyField('picker.League', blank=True)
    members = models.ManyToManyField('picker.PickerMembership', blank=True)
    status = models.CharField(
        max_length=4,
        choices=Status.CHOICES,
        default=Status.DEFAULT
    )


class PickerFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    league = models.ForeignKey('picker.League', on_delete=models.CASCADE)
    team = models.ForeignKey('picker.Team', on_delete=models.CASCADE)

    def __str__(self):
        return '{}: {} ({})'.format(self.user, self.team, self.league)

    def save(self, *args, **kws):
        if self.team.league != self.league:
            raise ValueError('Team {} not in league {}'.format(self.team, self.league))

        return super().save(*args, **kws)


class PickerMembership(models.Model):

    class Autopick(ChoiceEnumeration):
        NONE = ChoiceEnumeration.Option('NONE', 'None')
        RANDOM = ChoiceEnumeration.Option('RAND', 'Random', default=True)

    class Status(ChoiceEnumeration):
        ACTIVE = ChoiceEnumeration.Option('ACTV', 'Active', default=True)
        INACTIVE = ChoiceEnumeration.Option('IDLE', 'Inactive')
        SUSPENDED = ChoiceEnumeration.Option('SUSP', 'Suspended')
        MANAGER = ChoiceEnumeration.Option('MNGT', 'Manager')

    group = models.ForeignKey(PickerGrouping, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='picker_memberships'
    )
    status = models.CharField(max_length=4, choices=Status.CHOICES, default=Status.DEFAULT)
    autopick = models.CharField(max_length=4, choices=Autopick.CHOICES, default=Autopick.DEFAULT)


class League(models.Model):
    name = models.CharField(max_length=50, unique=True)
    abbr = models.CharField(max_length=8)
    logo = models.ImageField(upload_to=LOGOS_DIR, blank=True, null=True)
    is_pickable = models.BooleanField(default=False)

    objects = managers.LeagueManager()

    def __str__(self):
        return self.name

    def _reverse(self, name): return reverse(name, args=[self.lower])
    def get_absolute_url(self): return self._reverse('picker-home')
    def picks_url(self): return self._reverse('picker-picks')
    def results_url(self): return self._reverse('picker-results')
    def roster_url(self): return self._reverse('picker-roster')
    def teams_url(self): return self._reverse('picker-teams')
    def schedule_url(self): return self._reverse('picker-schedule')
    def manage_url(self): return self._reverse('picker-manage')

    @cached_property
    def lower(self):
        return self.abbr.lower()

    def _load_league_module(self, mod_name):
        base = picker_setting('LEAGUE_MODULE_BASE', 'picker.league')
        if base:
            try:
                return import_module('{}.{}.{}'.format(base, self.lower, mod_name))
            except ImportError:
                pass
        return None

    @cached_property
    def feed(self):
        url = self.config('FEED_URL')
        return parse_feed(url) if url else None

    @cached_property
    def scores_module(self):
        return self._load_league_module('scores')

    def scores(self, *args, **kws):
        mod = self.scores_module
        return mod.scores(*args, **kws) if mod else None

    def teams_by_conf(self):
        abbrs = self.conference_set.values('abbr', flat=True)
        confs = {abbr.lower(): [] for abbr in abbrs}
        for team in self.team_set.all():
            confs[team.conference.abbr.lower()].append(team)

        return confs

    def team_dict(self, aliases=True):
        names = {}
        for team in self.team_set.all():
            names[team.abbr] = team
            names[team.name] = team
            if team.nickname:
                names[team.nickname] = team

            if aliases:
                for a in Alias.objects.filter(team=team):
                    names[a.name] = team

            names[team.id] = team

        return names

    @property
    def latest_gameset(self):
        rel = datetime_now()
        try:
            return self.game_set.filter(closes__lte=rel).latest('closes')
        except GameSet.DoesNotExist:
            return None

    @property
    def latest_season(self):
        gs = self.latest_gameset
        return gs.season if gs else None

    @cached_property
    def current_gameset(self):
        rel = datetime_now()
        try:
            return self.game_set.get(opens__lte=rel, closes__gte=rel)
        except GameSet.DoesNotExist:
            return None

    @cached_property
    def current_playoffs(self):
        try:
            return self.playoff_set.get(season=self.current_season)
        except Playoff.DoesNotExist:
            return None

    @cached_property
    def available_seasons(self):
        return self.game_set.order_by('-season').values_list(
            'season',
            flat=True
        ).distinct()

    @cached_property
    def current_season(self):
        return self.config('CURRENT_SEASON', datetime_now().year)

    def season_weeks(self, season=None):
        season = season or self.current_season or self.latest_season
        return self.game_set.filter(season=season)

    def random_points(self):
        d = self.game_set.filter(points__gt=0).aggregate(
            stddev=models.StdDev('points'),
            avg=models.Avg('points')
        )
        avg = int(d['avg'])
        stddev = int(d['stddev'])
        return random.randint(avg - stddev, avg + stddev)

    def send_reminder_email(self):
        gs = self.current_gameset
        signals.picker_reminder.send(sender=GameSet, week=gs)

    def config(self, key, default=None):
        return picker_setting('{}_{}'.format(self.abbr.upper(), key), default)

    def create_season(self, season, schedule, byes=None):
        '''
        Create all GameSet and Game entries for a season, where:

        *   `season` is an int (2009)
        *   `schedule` is an iterable of 6-tuples of the following format:
            (sequence #, away, home, datetime or datetime-tuple, TV, location)

            Away and home teams are referenced by abbreviation.

            Example:

                (1, 'STL', 'SEA', (2009, 9, 13, 16, 15), 'CBS', 'Qwest Field')

        *   `byes` is a dictionary keyed by sequence number with the value being a
            list of team abbreviations

            Example:

                byes = {
                    4: ['ATL', 'PHI', 'ARI', 'CAR'],
                    5: ['CHI', 'GB', 'NO', 'LAC'],
                 ...
                }
        '''
        current_sequence = None
        game_set = None
        teams = self.team_dict()
        new_old = [0, 0]
        for sequence, away, home, dt, tv, where in schedule:
            away = teams[away]
            home = teams[home]
            dt = dt if isinstance(dt, datetime) else datetime(*dt)
            dt = dt.replace(tzinfo=UTC)

            if sequence != current_sequence:
                current_sequence = sequence

                opens = dt - timedelta(days=dt.weekday() - 1)
                opens = opens.replace(hour=12, minute=0)
                closes = opens + timedelta(days=6, seconds=3600*24-1)

                game_set, is_new = self.game_set.get_or_create(
                    season=season,
                    week=sequence,
                    defaults={'opens': opens, 'closes': closes}
                )
                if not is_new:
                    if game_set.opens != opens or game_set.closes != closes:
                        game_set.opens = opens
                        game_set.closes = closes
                        game_set.save()

                if byes and (sequence in byes):
                    game_set.byes.add(*[teams[t] for t in byes[sequence]])

            is_new = Game.objects.get_or_create(
                home=home,
                away=away,
                week=game_set,
                kickoff=dt,
                tv=tv,
                location=where,
            )[1]

            new_old[0 if is_new else 1] += 1
        return new_old

    # [
    #     "CIN",
    #     "IND",
    #     "2018-09-09T17:00Z",
    #     "CBS",
    #     "Lucas Oil Stadium, Indianapolis"
    # ],
    def import_games(self, season, filepath):
        with open(os.path.join(filepath)) as fp:
            data = json.loads(fp.read())

        game_set = None
        teams = self.team_dict()
        new_old = [0, 0]
        for sequence, item in enumerate(data):
            byes = item['byes']

            dt = parse_dt(item['games'][0][2])
            opens = dt - timedelta(days=dt.weekday() - 1)
            opens = opens.replace(hour=12, minute=0)
            closes = opens + timedelta(days=6, seconds=3600*24-1)

            game_set, is_new = self.game_set.get_or_create(
                season=season,
                week=sequence,
                defaults={'opens': opens, 'closes': closes}
            )
            if not is_new:
                if game_set.opens != opens or game_set.closes != closes:
                    game_set.opens = opens
                    game_set.closes = closes
                    game_set.save()

            if byes:
                game_set.byes.add(*[teams[t] for t in byes])

            for away, home, dt, tv, location in item['games']:
                away = teams[away]
                home = teams[home]
                dt = parse_dt(dt)

                is_new = Game.objects.get_or_create(
                    home=home,
                    away=away,
                    week=game_set,
                    kickoff=dt,
                    tv=tv,
                    location=location,
                )[1]

                new_old[0 if is_new else 1] += 1
        return new_old

    @staticmethod
    def import_league(filepath):
        with open(filepath) as fin:
            data = json.loads(fin.read())

        name = data['name']
        league, created = League.objects.get_or_create(
            name=name,
            abbr=data.get('abbr', ''.join(name.lower().split())),
            defaults={'is_pickable': data.get('is_pickable', False)},
        )
        confs = {}
        divs = {}
        teams = {}
        for tm in data['teams']:
            conf, div = tm['sub']
            if conf not in confs:
                confs[conf] = Conference.objects.get_or_create(
                    name=conf,
                    league=league,
                    abbr=conf.lower()
                )[0]

            if (div, conf) not in divs:
                divs[(div, conf)] = Division.objects.get_or_create(
                name=name,
                conference=confs[conf]
            )[0]

            teams[tm['abbr']] = Team.objects.get_or_create(
                name=tm['name'],
                abbr=tm['abbr'],
                nickname=tm['nickname'],
                league=league,
                conference=confs[conf],
                division=divs[(div, conf)],
                logo='picker/logos/{}.gif'.format(league.abbr.lower())
            )[0]

        return league, teams

    @classmethod
    def get(cls, abbr=None):
        abbr = abbr or picker_setting('DEFAULT_LEAGUE', 'nfl')
        return League.objects.get(abbr=abbr)


class Conference(models.Model):
    name = models.CharField(max_length=50)
    abbr = models.CharField(max_length=8)
    league = models.ForeignKey(League, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Division(models.Model):
    name = models.CharField(max_length=50)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Team(models.Model):
    '''
    Common team attributes.
    '''

    name = models.CharField(max_length=50)
    abbr = models.CharField(max_length=8, blank=True)
    nickname = models.CharField(max_length=50)
    location = models.CharField(max_length=100, blank=True)
    image = models.CharField(max_length=50, blank=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.SET_NULL, blank=True, null=True)
    colors = models.CharField(max_length=40, blank=True)
    logo = models.ImageField(upload_to=LOGOS_DIR, blank=True, null=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return '{} {}'.format(self.name, self.nickname)

    def get_absolute_url(self):
        return reverse('picker-team', args=[self.league.lower, self.abbr])

    @property
    def aliases(self):
        return ','.join(self.alias_set.values_list('name', flat=True))

    @aliases.setter
    def aliases(self, values):
        self.alias_set.all().delete()
        for value in values.split(','):
            self.alias_set.create(name=value.strip())

    @property
    def lower(self):
        return self.abbr.lower()

    def season_record(self, season=None):
        season = season or self.league.current_season
        wins, losses, ties = (0, 0, 0)
        for game in Game.objects.exclude(status=Game.Status.UNPLAYED).filter(
            models.Q(home=self) | models.Q(away=self),
            week__season=season,
        ):
            if game.winner.id == self.id:
                wins += 1
            elif game.status == Game.Status.TIE:
                ties += 1
            else:
                losses += 1

        return (wins, losses, ties) if ties else (wins, losses)

    def season_points(self, season=None):
        season = season or self.league.current_season
        w, l, t = self.season_record(season)
        return ((w - l) * 2) + t

    @property
    def record(self):
        return self.season_record(self.league.current_season)

    @property
    def record_as_string(self):
        return '-'.join(str(s) for s in self.record)

    @property
    def color_options(self):
        return self.colors.split(',')

    @property
    def playoff(self):
        try:
            return self.playoff_set.get(season=self.current_season)
        except Playoff.DoesNotExist:
            return None

    def schedule(self, season=None):
        return Game.objects.select_related('week').filter(
            models.Q(away=self) | models.Q(home=self),
            week__season=season or self.league.current_season
        )

    def bye_week(self, season=None):
        return self.bye_set.get(season=season or self.league.current_season)

    def complete_record(self):
        home_games = [0, 0, 0]
        away_games = [0, 0, 0]

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


class Alias(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class GameSet(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='game_set')
    season = models.PositiveSmallIntegerField()
    week = models.PositiveSmallIntegerField()
    points = models.PositiveSmallIntegerField(default=0)
    opens = models.DateTimeField()
    closes = models.DateTimeField()
    byes = models.ManyToManyField(
        Team,
        blank=True,
        verbose_name='Bye Teams',
        related_name='bye_set'
    )

    class Meta:
        ordering = ('season', 'week')

    def __str__(self):
        return '{}:{}'.format(self.sequence, self.season)

    @property
    def sequence(self):
        return self.week

    def get_absolute_url(self):
        return reverse(
            'picker-game-sequence',
            args=[self.league.lower, str(self.season), str(self.sequence)]
        )

    def picks_url(self):
        return reverse(
            'picker-picks-sequence',
            args=[self.league.lower, str(self.season), str(self.sequence)]
        )

    @property
    def last_game(self):
        return self.games[-1]

    @property
    def first_game(self):
        return self.games[0]

    @cached_property
    def kickoff(self):
        return self.first_game.kickoff

    @property
    def end_time(self):
        return self.last_game.end_time

    @property
    def in_progress(self):
        return self.end_time >= datetime_now() >= self.kickoff

    @property
    def has_started(self):
        return datetime_now() >= self.kickoff

    @property
    def is_open(self):
        return datetime_now() < self.last_game.kickoff

    @cached_property
    def games(self):
        return tuple(self.game_set.order_by('kickoff'))

    @property
    def winners(self):
        winners = []
        if self.points:
            for place, item in self.weekly_results():
                if place > 1:
                    break
                winners.append(item.user)
        return winners

    def update_pick_status(self):
        for wp in self.pick_set.all():
            wp.update_status()

    def pick_for_user(self, user):
        try:
            return self.pick_set.select_related().get(user=user)
        except PickSet.DoesNotExist:
            return None

    def create_picks_for_user(self, user, strategy, send_confirmation=True):
        Strategy = self.model.Strategy
        is_auto = (strategy == Strategy.RANDOM)
        picks = self.pick_set.create(
            user=user,
            points=self.league.random_points() if is_auto else 0,
            strategy=strategy
        )
        picks.complete_picks(is_auto, self.game_set.all())
        if send_confirmation:
            picks.send_confirmation(is_auto)

        return picks

    def picks_kickoff(self):
        force_autopick = self.league.config('FORCE_AUTOPICK', True)
        Strategy = PickSet.Strategy
        for pref in Preference.objects.active():
            auto = True if force_autopick else pref.should_autopick
            wp = self.pick_for_user(pref.user)
            if wp:
                wp.complete_picks(auto, list(self.game_set.all()))
            elif can_user_participate(pref, self):
                strategy = Strategy.RANDOM if auto else Strategy.USER
                self.create_picks_for_user(pref.user, strategy, True)

    def update_results(self):
        results = self.league.scores(completed=True)
        if not results:
            raise PickerResultException('Results unavailable')

        completed = {g['home']: g for g in results}
        if not completed:
            raise PickerResultException('No completed results')

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

        last_game = self.last_game
        if not self.points and last_game.winner:
            now = datetime_now()
            if now > last_game.end_time:
                result = completed.get(last_game.home.abbr, None)
                if result:
                    self.points = result['home_score'] + result['away_score']
                    self.save()

        if count:
            self.update_pick_status()

        return (count, self.points)

    def set_default_open_and_close(self):
        prv = rd.relativedelta(weekday=rd.TU(-1))
        nxt = rd.relativedelta(weekday=rd.TU)
        for gs in self.game_set.all():
            ko = gs.kickoff
            gs.opens = (ko + prv).replace(hour=12, minute=0)
            gs.closes = (ko + nxt).replace(hour=11, minute=59, second=59)
            gs.save()

    def weekly_results(self):
        picks = list(self.pick_set.select_related())
        return sorted_standings(
            picks,
            key=lambda ps: (ps.correct, -ps.points_delta),
            reverse=True
        )


class Game(models.Model):

    class Category(ChoiceEnumeration):
        REGULAR = ChoiceEnumeration.Option('REG', 'Regular Season', default=True)
        POST = ChoiceEnumeration.Option('POST', 'Post Season')
        PRE = ChoiceEnumeration.Option('PRE', 'Pre Season')
        FRIENDLY = ChoiceEnumeration.Option('FRND', 'Friendly')

    class Status(ChoiceEnumeration):
        UNPLAYED = ChoiceEnumeration.Option('U', 'Unplayed', default=True)
        TIE = ChoiceEnumeration.Option('T', 'Tie')
        HOME_WIN = ChoiceEnumeration.Option('H', 'Home Win')
        AWAY_WIN = ChoiceEnumeration.Option('A', 'Away Win')
        CANCELLED = ChoiceEnumeration.Option('X', 'Cancelled')

    home = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_game_set')
    away = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_game_set')
    week = models.ForeignKey(GameSet, on_delete=models.CASCADE, related_name='game_set')
    kickoff = models.DateTimeField()
    tv = models.CharField('TV', max_length=8, blank=True)
    notes = models.TextField(blank=True)
    category = models.CharField(max_length=4, choices=Category.CHOICES, default=Category.DEFAULT)
    status = models.CharField(max_length=1, choices=Status.CHOICES, default=Status.DEFAULT)
    location = models.CharField(blank=True, max_length=50)
    objects = managers.GameManager()

    class Meta:
        ordering = ('kickoff', 'away')

    def __str__(self):
        return '{} {}'.format(self.tiny_description, self.game_set)

    @property
    def game_set(self):
        return self.week

    @property
    def has_started(self):
        return datetime_now() >= self.kickoff

    @property
    def tiny_description(self):
        return '%s @ %s' % (self.away.abbr, self.home.abbr)

    @property
    def short_description(self):
        return '%s @ %s' % (self.away, self.home)

    @property
    def vs_description(self):
        return '%s vs %s' % (self.away.nickname, self.home.nickname)

    @property
    def long_description(self):
        return '%s %s %s' % (self.short_description, self.game_set, self.kickoff)

    @property
    def winner(self):
        if self.status == self.Status.HOME_WIN:
            return self.home

        if self.status == self.Status.AWAY_WIN:
            return self.away

        return None

    @winner.setter
    def winner(self, team):
        if team is None:
            self.status = self.Status.TIE
        elif team == self.away:
            self.status = self.Status.AWAY_WIN
        elif team == self.home:
            self.status = self.Status.HOME_WIN
        else:
            return

        self.save()

    def auto_pick_winner(self, pick_strategy=None):
        if pick_strategy == PickSet.Strategy.HOME:
            return self.home

        if pick_strategy == PickSet.Strategy.BEST:
            a, b = self.home.season_points(), self.away.season_points()
            return self.home if a >= b else self.away

        return random.choice((self.home, self.away))

    @property
    def end_time(self):
        return self.kickoff + GAME_DURATION

    @property
    def in_progress(self):
        now = datetime_now()
        return self.end_time >= now >= self.kickoff


class PickSet(models.Model):

    class Strategy(ChoiceEnumeration):
        USER = ChoiceEnumeration.Option('USER', 'User', default=True)
        RANDOM = ChoiceEnumeration.Option('RAND', 'Random')
        HOME = ChoiceEnumeration.Option('HOME', 'Home Team')
        BEST = ChoiceEnumeration.Option('BEST', 'Best Record')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pick_set'
    )

    week = models.ForeignKey(GameSet, on_delete=models.CASCADE, related_name='pick_set')
    points = models.PositiveSmallIntegerField(default=0)
    correct = models.PositiveSmallIntegerField(default=0)
    wrong = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    strategy = models.CharField(max_length=4, choices=Strategy.CHOICES, default=Strategy.DEFAULT)
    is_winner = models.BooleanField(default=False)

    class Meta:
        unique_together = (('user', 'week'),)

    def __str__(self):
        return '%s %s %d' % (self.game_set, self.user, self.correct)

    @property
    def game_set(self):
        return self.week

    @property
    def is_autopicked(self):
        return self.strategy != self.Strategy.USER

    @property
    def is_complete(self):
        return (
            False if self.points is None
            else (self.progress == len(self.game_set.games))
        )

    @property
    def progress(self):
        return self.gamepick_set.filter(winner__isnull=False).count()

    def update_status(self):
        picks = self.gamepick_set.all()
        self.correct = sum([1 for gp in picks if gp.is_correct])
        self.wrong = len(picks) - self.correct
        self.save()
        return self.correct

    @property
    def points_delta(self):
        if self.game_set.points == 0:
            return 0

        return abs(self.points - self.game_set.points)

    def send_confirmation(self, auto_pick=False):
        signals.picker_confirmation.send(
            sender=self.__class__,
            weekly_picks=self,
            auto_pick=auto_pick
        )

    def complete_picks(self, is_random=True, games=None):
        games = games or self.game_set.all()
        picked_games = set((gp.game for gp in self.gamepick_set.all()))
        for g in games:
            if g not in picked_games:
                w = g.auto_pick_winner(self.Strategy.RANDOM) if is_random else None
                self.gamepick_set.create(game=g, winner=w)


class GamePick(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='gamepick_set')
    winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    pick = models.ForeignKey(PickSet, on_delete=models.CASCADE)

    objects = managers.GamePickManager()

    class Meta:
        ordering = ('game__kickoff', 'game__away')

    @property
    def kickoff(self):
        return self.game.kickoff

    @property
    def short_description(self):
        return self.game.short_description

    def __str__(self):
        return '%s: %s - Game %d' % (self.pick.user, self.winner, self.game.id)

    @property
    def winner_abbr(self):
        return self.winner.abbr if self.winner else 'N/A'

    @property
    def picked_home(self):
        return self.winner == self.game.home

    @property
    def is_correct(self):
        winner = self.game.winner
        if winner:
            return self.winner == winner

        return None


class PlayoffResult(Attr):

    def __repr__(self):
        return '%d,%d,%s' % (self.score, self.delta, self.picks)


class Playoff(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    season = models.PositiveSmallIntegerField()
    kickoff = models.DateTimeField()

    @cached_property
    def seeds(self):
        return [(p.seed, p.team) for p in self.playoffteam_set.all()]

    @property
    def picks(self):
        return PlayoffPicks.objects.filter(self.league, season=self.season)

    def user_picks(self, user):
        return self.playoffpicks_set.get_or_create(user=user)[0]

    @property
    def admin(self):
        return self.playoffpicks_set.get_or_create(
            user__isnull=True,
            defaults={'picks': {}}
        )[0]

    @property
    def scores(self):
        results = []
        teams = {t.abbr: t for t in self.playoffteam_set.all()}
        admin = self.admin
        pts_dct = self.league.config('PLAYOFF_SCORE')
        for pck in self.playoffpicks_set.filter(user__isnull=False):
            points, pck_res = 0, []
            for i, (a_tm, p_tm) in enumerate(zip(admin.teams, pck.teams), 1):
                if (a_tm and p_tm) and (a_tm == p_tm):
                    good = pts_dct.get(i, 1)
                else:
                    good = 0

                points += good
                pck_res.append((good, teams[p_tm] if p_tm else None))
            results.append((points, -abs(admin.points - pck.points), pck, pck_res))

        return [
            PlayoffResult(score=score, delta=delta, picks=picks, results=res)
            for score, delta, picks, res in sorted(results, reverse=True)
        ]

    @property
    def has_started(self):
        return self.kickoff < datetime_now()


class PlayoffTeam(models.Model):
    playoff = models.ForeignKey(Playoff, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    seed = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ('seed',)


class PlayoffPicks(models.Model):
    playoff = models.ForeignKey(Playoff, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    picks = JSONField()

    def __str__(self):
        return str(self.user) if self.user else '<admin>'

    @cached_property
    def season(self):
        return self.playoff.season

    @property
    def teams(self):
        return tuple([self.picks.get('game_%d' % i) for i in range(1, 12)])

    @property
    def teams_by_round(self):
        teams = self.teams
        return tuple([teams[:4], teams[4:8], teams[8:10], teams[10:]])

    @property
    def points(self):
        pts = self.picks.get('points', '')
        return int(pts) if pts.isdigit() else 0


class RosterStats:

    def __init__(self, preference, league, season=None):
        self.preference = preference
        self.user = preference.user
        self.season = season
        self.league = league
        self.correct = 0
        self.wrong = 0
        self.points_delta = 0

        qs = self.user.pick_set.filter(week__league=league).select_related().filter(
            models.Q(correct__gt=0) | models.Q(wrong__gt=0)
        )

        if season:
            qs = qs.filter(week__season=season)

        self.weeks_played = 0
        for wp in qs:
            self.weeks_played += 1
            self.correct += wp.correct
            self.wrong += wp.wrong
            self.points_delta += wp.points_delta if wp.week.points else 0

        self.is_active = self.preference.is_active
        self.pct = percent(self.correct, self.correct + self.wrong)
        self.avg_points_delta = (
            float(self.points_delta) / self.weeks_played
            if self.weeks_played
            else 0
        )

    @property
    def weeks_won(self):
        query = GameSet.objects.filter(pick_set__is_winner=True, pick_set__user=self.user)
        if self.season:
            query = query.filter(season=self.season)

        return list(query.select_related())

    def __str__(self):
        return '{}{}'.format(self.user, ' ({})'.format(self.season) if self.season else '')

    __repr__ = __str__

    @staticmethod
    def get_details(league, season=None):
        season = season or league.current_season
        prefs = Preference.objects.filter(
            league=league
        ).select_related().order_by('user__username')

        def keyfn(rs):
            return (rs.correct, -rs.points_delta, rs.weeks_played)

        stats = [RosterStats(p, league) for p in prefs]
        by_user = {
            entry.user: entry for entry in sorted_standings(stats, key=keyfn)
        }

        stats = [RosterStats(p, league, season) for p in prefs]
        return [
            (e, by_user[e.user]) for e in sorted_standings(stats, key=keyfn)
        ]


def sorted_standings(items, key=None, reverse=True):
    weighted = []
    prev_place, prev_results = 1, (0, 0)
    for i, item in enumerate(sorted(items, reverse=reverse, key=key), 1):
        results = (item.correct, item.points_delta)
        item.place = prev_place if results == prev_results else i
        prev_place, prev_results = item.place, results
        weighted.append(item)

    return weighted


__participation_hooks = None


def can_user_participate(pref, week):
    global __participation_hooks
    if __participation_hooks is None:
        hooks = picker_setting('PARTICIPATION_HOOKS', [])
        __participation_hooks = [import_string(hook) for hook in hooks]

    for hook in __participation_hooks:
        if not hook(pref, week):
            return False

    return True
