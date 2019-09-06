from collections import OrderedDict
from django.db import models
from .utils import datetime_now


class PreferenceManager(models.Manager):

    def for_user(self, user):
        return self.get_or_create(user=user)[0]


class LeagueManager(models.Manager):

    def pickable(self, **kws):
        return self.filter(is_pickable=True, **kws)


class GamePickManager(models.Manager):

    def games_started(self):
        return self.filter(game__start_time__lte=datetime_now())

    def games_started_display(self):
        return self.games_started().values_list('game__id', 'winner__abbr')

    def picked_winner_ids(self):
        return self.filter(winner__isnull=False).values_list('game__id', 'winner__id')


class GameManager(models.Manager):

    def display_results(self):
        return OrderedDict([
            (item['id'], item) for item in self.games_started().annotate(
                winner=models.Case(
                    models.When(status='H', then='home__abbr'),
                    models.When(status='A', then='away__abbr'),
                    models.When(status='T', then=models.Value('__TIE__')),
                    default=None,
                    output_field=models.CharField()
                )
            ).values('id', 'home__abbr', 'away__abbr', 'winner')
        ])

    def games_started(self):
        return self.filter(start_time__lte=datetime_now())

    def incomplete(self, **kws):
        kws['status'] = self.model.Status.UNPLAYED
        return self.filter(**kws)

    def played(self, **kws):
        Status = self.model.Status
        kws['status__in'] = [Status.TIE, Status.HOME_WIN, Status.AWAY_WIN]
        return self.filter(**kws)


class PickSetManager(models.Manager):

    def for_gameset_user(self, gameset, user, strategy=None, autopick=False):
        Strategy = self.model.Strategy
        strategy = strategy or Strategy.USER
        picks, created = self.get_or_create(
            gameset=gameset,
            user=user,
            defaults={'strategy': strategy}
        )
        if created and autopick:
            picks.points = gameset.league.random_points()
            picks.save()

        games = set(gameset.games.values_list('id', flat=True))
        if not created:
            games -= set(picks.gamepicks.values_list('game__id', flat=True))

        for game in gameset.games.filter(id__in=games).select_related():
            winner = game.get_random_winner() if autopick else None
            picks.gamepicks.create(game=game, winner=winner)

        return picks
