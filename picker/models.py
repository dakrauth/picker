# -*- coding:utf8 -*-
import random
import itertools
from datetime import timedelta
from collections import ChainMap

from django.db import models
from django.urls import reverse
from django.conf import settings
from django.dispatch import Signal
from django.db import OperationalError
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError

from dateutil.parser import parse as parse_dt
from choice_enum import ChoiceEnumeration
from django_extensions.db.fields.json import JSONField

from .exceptions import PickerResultException
from .conf import picker_settings
from . import managers
from . import utils
from . import importers
from .utils import datetime_now

LOGOS_DIR = picker_settings.get('LOGOS_UPLOAD_DIR', 'picker/logos')


class Preference(models.Model):

    class Autopick(ChoiceEnumeration):
        NONE = ChoiceEnumeration.Option('NONE', 'None')
        RAND = ChoiceEnumeration.Option('RAND', 'Random', default=True)

    autopick = models.CharField(max_length=4, choices=Autopick.CHOICES, default=Autopick.DEFAULT)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='picker_preferences'
    )

    objects = managers.PreferenceManager()

    def __str__(self):
        return str('{} Preference'.format(self.user))

    @property
    def should_autopick(self):
        return self.autopick != self.Autopick.NONE


class PickerGrouping(models.Model):
    class Category(ChoiceEnumeration):
        PUBLIC = ChoiceEnumeration.Option('PUB', 'Public')
        PROTECTED = ChoiceEnumeration.Option('PRT', 'Protected')
        PRIVATE = ChoiceEnumeration.Option('PVT', 'Private', default=True)

    class Status(ChoiceEnumeration):
        ACTIVE = ChoiceEnumeration.Option('ACTV', 'Active', default=True)
        INACTIVE = ChoiceEnumeration.Option('IDLE', 'Inactive')

    name = models.CharField(max_length=75, unique=True)
    leagues = models.ManyToManyField('picker.League', blank=True)
    status = models.CharField(
        max_length=4,
        choices=Status.CHOICES,
        default=Status.DEFAULT
    )
    category = models.CharField(
        max_length=3,
        choices=Category.CHOICES,
        default=Category.DEFAULT
    )

    def __str__(self):
        return self.name


class PickerFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    league = models.ForeignKey('picker.League', on_delete=models.CASCADE)
    team = models.ForeignKey('picker.Team', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return '{}: {} ({})'.format(self.user, self.team, self.league)

    def save(self, *args, **kws):
        if self.team and self.team.league != self.league:
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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='picker_memberships'
    )
    group = models.ForeignKey(PickerGrouping, on_delete=models.CASCADE, related_name='members')
    status = models.CharField(max_length=4, choices=Status.CHOICES, default=Status.DEFAULT)
    autopick = models.CharField(max_length=4, choices=Autopick.CHOICES, default=Autopick.DEFAULT)

    def __str__(self):
        return str(self.user)

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_management(self):
        return self.status == self.Status.MANAGER


def temp_slug():
    return '{:10.0f}'.format(random.random() * 10000000000)


class League(models.Model):
    name = models.CharField(max_length=50, unique=True)
    abbr = models.CharField(max_length=8)
    logo = models.ImageField(upload_to=LOGOS_DIR, blank=True, null=True)
    is_pickable = models.BooleanField(default=False)
    current_season = models.IntegerField(blank=True, null=True)
    slug = models.SlugField(default=temp_slug)
    avg_game_duration = models.PositiveIntegerField(default=240)

    objects = managers.LeagueManager()

    class Meta:
        permissions = (("can_update_score", "Can update scores"),)

    def __str__(self):
        return self.name

    def _reverse(self, name): return reverse(name, args=[self.slug])
    def get_absolute_url(self): return self._reverse('picker-home')
    def picks_url(self): return self._reverse('picker-picks')
    def results_url(self): return self._reverse('picker-results')
    def roster_url(self): return self._reverse('picker-roster-base')
    def teams_url(self): return self._reverse('picker-teams')
    def schedule_url(self): return self._reverse('picker-schedule')
    def manage_url(self): return self._reverse('picker-manage')

    @cached_property
    def team_dict(self):
        names = {}
        for team in self.teams.all():
            names[team.abbr] = team
            names[team.id] = team
            if team.nickname:
                full_name = '{} {}'.format(team.name, team.nickname)
                names[full_name] = team

            for alias in Alias.objects.filter(team=team).values_list('name', flat=True):
                names[alias] = team

        return names

    @property
    def latest_gameset(self):
        rel = datetime_now()
        try:
            return self.gamesets.filter(points=0, opens__gte=rel).earliest('opens')
        except GameSet.DoesNotExist:
            pass

        try:
            return self.gamesets.filter(closes__lte=rel).latest('closes')
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
            return self.gamesets.get(opens__lte=rel, closes__gte=rel)
        except GameSet.DoesNotExist:
            return None

    @cached_property
    def available_seasons(self):
        return self.gamesets.order_by('-season').values_list(
            'season',
            flat=True
        ).distinct()

    def season_gamesets(self, season=None):
        season = season or self.current_season or self.latest_season
        return self.gamesets.filter(season=season)

    def random_points(self):
        try:
            d = self.gamesets.filter(points__gt=0).aggregate(
                stddev=models.StdDev('points'),
                avg=models.Avg('points')
            )
        except OperationalError:
            return 0
        else:
            avg = int(d['avg'])
            stddev = int(d['stddev'])
            return random.randint(avg - stddev, avg + stddev)

    @cached_property
    def _config(self):
        core = {}
        base = {}
        league = {}
        for key, value in picker_settings.items():
            if key == '_BASE':
                base = picker_settings[key]
            elif isinstance(value, dict) and key == self.abbr:
                league = value
            else:
                core[key] = value

        return ChainMap(league, base, core)

    def config(self, key, default=None):
        return self._config.get(key, default)

    @classmethod
    def import_season(cls, data):
        return importers.import_season(cls, data)

    @classmethod
    def import_league(cls, data):
        return importers.import_league(cls, data)

    @classmethod
    def get(cls, abbr=None):
        abbr = abbr or picker_settings.get('DEFAULT_LEAGUE', 'nfl')
        return cls.objects.get(abbr__iexact=abbr)


class Conference(models.Model):
    name = models.CharField(max_length=50)
    abbr = models.CharField(max_length=8)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='conferences')

    def __str__(self):
        return self.name


class Division(models.Model):
    name = models.CharField(max_length=50)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name='divisions')

    def __str__(self):
        return '{} {}'.format(self.conference.name, self.name)


def valid_team_abbr(value):
    if value.startswith('__'):
        raise ValidationError('Team abbr cannot start with "__"')


class Team(models.Model):
    '''
    Common team attributes.
    '''

    name = models.CharField(max_length=50)
    abbr = models.CharField(max_length=8, blank=True, validators=[valid_team_abbr])
    nickname = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)
    coach = models.CharField(max_length=50, blank=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='teams')
    conference = models.ForeignKey(
        Conference,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='teams'
    )
    division = models.ForeignKey(
        Division,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='teams'
    )
    colors = models.CharField(max_length=40, blank=True)
    logo = models.ImageField(upload_to=LOGOS_DIR, blank=True, null=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return '{} {}'.format(self.name, self.nickname)

    def get_absolute_url(self):
        return reverse('picker-team', args=[self.league.slug, self.abbr])

    def season_record(self, season=None):
        season = season or self.league.current_season
        wins, losses, ties = (0, 0, 0)
        for status, home_abbr, away_abbr in Game.objects.filter(
            models.Q(home=self) | models.Q(away=self),
            gameset__season=season,
        ).exclude(
            status__in=[Game.Status.UNPLAYED, Game.Status.CANCELLED]
        ).values_list('status', 'home__abbr', 'away__abbr'):
            if status == Game.Status.TIE:
                ties += 1
            else:
                if (
                    (status == Game.Status.HOME_WIN and self.abbr == home_abbr) or
                    (status == Game.Status.AWAY_WIN and self.abbr == away_abbr)
                ):
                    wins += 1
                else:
                    losses += 1

        return (wins, losses, ties)

    def season_points(self, season=None):
        season = season or self.league.current_season
        w, l, t = self.season_record(season)
        return w * 2 + t

    @property
    def record(self):
        return self.season_record(self.league.current_season)

    @property
    def record_as_string(self):
        record = self.record
        if not record[2]:
            record = record[:2]
        return '-'.join(str(s) for s in record)

    @property
    def color_options(self):
        return self.colors.split(',') if self.colors else []

    def schedule(self, season=None):
        return Game.objects.select_related('gameset').filter(
            models.Q(away=self) | models.Q(home=self),
            gameset__season=season or self.league.current_season
        )

    def byes(self, season=None):
        return self.bye_set.filter(season=season or self.league.current_season)

    def complete_record(self):
        home_games = [0, 0, 0]
        away_games = [0, 0, 0]

        for games, accum, status in (
            (self.away_games, away_games, Game.Status.AWAY_WIN),
            (self.home_games, home_games, Game.Status.HOME_WIN),
        ):
            for res in games.exclude(status=Game.Status.UNPLAYED).values_list(
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
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='aliases')
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class GameSet(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='gamesets')
    season = models.PositiveSmallIntegerField()
    sequence = models.PositiveSmallIntegerField()
    points = models.PositiveSmallIntegerField(default=0)
    opens = models.DateTimeField()
    closes = models.DateTimeField()
    description = models.CharField(max_length=60, default='', blank=True)
    byes = models.ManyToManyField(
        Team,
        blank=True,
        verbose_name='Bye Teams',
        related_name='bye_set'
    )

    class Meta:
        ordering = ('season', 'sequence')

    def __str__(self):
        return '{}:{}'.format(self.sequence, self.season)

    def get_absolute_url(self):
        return reverse(
            'picker-game-sequence',
            args=[self.league.slug, str(self.season), str(self.sequence)]
        )

    def picks_url(self):
        return reverse(
            'picker-picks-sequence',
            args=[self.league.slug, str(self.season), str(self.sequence)]
        )

    def import_games(self, data, teams=None):
        teams = teams or self.league.team_dict
        byes = data.get('byes')
        if byes:
            self.byes.add(*[teams[t] for t in byes])

        games = []
        for dct in data['games']:
            start_time = parse_dt(dct['start'])
            game, is_new = self.games.get_or_create(
                home=teams[dct['home']],
                away=teams[dct['away']],
                defaults={'start_time': start_time}
            )
            game.start_time = start_time
            game.tv = dct.get('tv', game.tv)
            game.location = dct.get('location', game.location)
            game.save()
            games.append([game, is_new])

        return games

    @property
    def last_game(self):
        return self.games.last()

    @property
    def first_game(self):
        return self.games.first()

    @cached_property
    def start_time(self):
        return self.first_game.start_time

    @property
    def end_time(self):
        return self.last_game.end_time

    @property
    def in_progress(self):
        return self.end_time >= datetime_now() >= self.start_time

    @property
    def has_started(self):
        return datetime_now() >= self.start_time

    @property
    def is_open(self):
        return datetime_now() < self.last_game.start_time

    def pick_for_user(self, user):
        try:
            return self.picksets.select_related().get(user=user)
        except PickSet.DoesNotExist:
            return None

    def reset_games_status(self):
        UNPLAYED = Game.Status.UNPLAYED
        self.games.exclude(status=UNPLAYED).update(status=UNPLAYED)

    def update_results(self, results):
        '''
        results schema: {'sequence': 1, 'season': 2018, 'games': [{
            "home": "HOME",
            "away": "AWAY",
            "home_score": 15,
            "away_score": 10,
            "status": "Final",
            "winner": "HOME",
        }]}
        '''

        if not results:
            raise PickerResultException('Results unavailable')

        if results['sequence'] != self.sequence or results['season'] != self.season:
            raise PickerResultException('Results not updated, wrong season or week')

        completed = {g['home']: g for g in results['games'] if g['status'].startswith('F')}
        if not completed:
            return (0, None)

        count = 0
        for game in self.games.incomplete(home__abbr__in=completed.keys()):
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

    def winners(self):
        if self.points:
            yield from itertools.takewhile(lambda i: i.place == 1, self.results())

    def update_pick_status(self):
        winners = set(w.id for w in self.winners())
        for wp in self.picksets.all():
            wp.update_status(wp.id in winners)

    def results(self):
        picks = list(self.picksets.select_related())
        return utils.sorted_standings(picks, key=PickSet.sort_key, reverse=True)


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

    home = models.ForeignKey(
        Team,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='home_games'
    )
    away = models.ForeignKey(
        Team,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='away_games'
    )
    gameset = models.ForeignKey(GameSet, on_delete=models.CASCADE, related_name='games')
    start_time = models.DateTimeField()
    tv = models.CharField('TV', max_length=8, blank=True)
    notes = models.TextField(blank=True)
    category = models.CharField(max_length=4, choices=Category.CHOICES, default=Category.DEFAULT)
    status = models.CharField(max_length=1, choices=Status.CHOICES, default=Status.DEFAULT)
    location = models.CharField(blank=True, default='', max_length=60)
    description = models.CharField(max_length=60, default='', blank=True)

    objects = managers.GameManager()

    class Meta:
        ordering = ('start_time', 'away')

    def __str__(self):
        return '{} @ {} {}'.format(self.away.abbr, self.home.abbr, self.gameset)

    @property
    def is_tie(self):
        return self.status == self.Status.TIE

    @property
    def has_started(self):
        return datetime_now() >= self.start_time

    @property
    def short_description(self):
        return '%s @ %s' % (self.away, self.home)

    @property
    def vs_description(self):
        return '%s vs %s' % (self.away.nickname, self.home.nickname)

    @property
    def is_home_win(self):
        return self.status == self.Status.HOME_WIN

    @property
    def is_away_win(self):
        return self.status == self.Status.AWAY_WIN

    @property
    def is_tie(self):
        return self.status == self.Status.TIE

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

    def get_random_winner(self):
        return random.choice((self.home, self.away))

    @property
    def end_time(self):
        return self.start_time + timedelta(minutes=self.gameset.league.avg_game_duration)

    @property
    def in_progress(self):
        now = datetime_now()
        return self.end_time >= now >= self.start_time


class PickSet(models.Model):

    class Strategy(ChoiceEnumeration):
        USER = ChoiceEnumeration.Option('USER', 'User', default=True)
        RANDOM = ChoiceEnumeration.Option('RAND', 'Random')
        HOME = ChoiceEnumeration.Option('HOME', 'Home Team')
        BEST = ChoiceEnumeration.Option('BEST', 'Best Record')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='picksets'
    )

    gameset = models.ForeignKey(GameSet, on_delete=models.CASCADE, related_name='picksets')
    points = models.PositiveSmallIntegerField(default=0)
    correct = models.PositiveSmallIntegerField(default=0)
    wrong = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    strategy = models.CharField(max_length=4, choices=Strategy.CHOICES, default=Strategy.DEFAULT)
    is_winner = models.BooleanField(default=False)

    objects = managers.PickSetManager()

    updated_signal = Signal(providing_args=['pickset', 'auto_pick'])

    class Meta:
        unique_together = (('user', 'gameset'),)

    def __str__(self):
        return '%s %s %d' % (self.gameset, self.user, self.correct)

    def sort_key(self):
        return (self.correct, -self.points_delta)

    @property
    def is_autopicked(self):
        return self.strategy != self.Strategy.USER

    @property
    def is_complete(self):
        return (
            False if self.points == 0
            else (self.progress == self.gameset.games.count())
        )

    @property
    def progress(self):
        return self.gamepicks.filter(winner__isnull=False).count()

    def update_status(self, is_winner=False):
        picks = self.gamepicks.all()
        self.correct = sum([1 for gp in picks if gp.is_correct])
        self.wrong = len(picks) - self.correct
        self.is_winner = is_winner
        self.save()
        return self.correct

    @property
    def points_delta(self):
        if self.gameset.points == 0:
            return 0

        return abs(self.points - self.gameset.points)

    def update_picks(self, games=None, points=None):
        '''
        games can be dict of {game.id: winner_id} for all picked games to update
        '''
        if games:
            game_dict = {g.id: g for g in self.gameset.games.filter(id__in=games)}
            game_picks = {pick.game.id: pick for pick in self.gamepicks.filter(game__id__in=games)}
            for key, winner in games.items():
                game = game_dict[key]
                if not game.has_started:
                    pick = game_picks[key]
                    pick.winner_id = winner
                    pick.save()

        if points is not None:
            self.points = points
            self.save()

        if games or points:
            self.updated_signal.send(sender=self.__class__, pickset=self, auto_pick=False)


class GamePick(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='gamepicks')
    winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    pick = models.ForeignKey(PickSet, on_delete=models.CASCADE, related_name='gamepicks')

    objects = managers.GamePickManager()

    class Meta:
        ordering = ('game__start_time', 'game__away')

    def __str__(self):
        return '%s: %s - Game %d' % (self.pick.user, self.winner, self.game.id)

    def set_random_winner(self, force=False):
        if self.winner is None or force:
            self.winner = self.game.get_random_winner()
            self.save()

    @property
    def start_time(self):
        return self.game.start_time

    @property
    def short_description(self):
        return self.game.short_description

    @property
    def winner_abbr(self):
        return self.winner.abbr if self.winner else 'N/A'

    @property
    def picked_home(self):
        return self.winner == self.game.home

    @property
    def picked_away(self):
        return self.winner == self.game.away

    @property
    def is_correct(self):
        winner = self.game.winner
        if winner:
            return self.winner == winner

        return None
