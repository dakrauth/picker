from django.db.models import Q
from .models import GameSet
from .utils import sorted_standings


def percent(num, denom):
    return 0.0 if denom == 0 else (float(num) / denom) * 100.0


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
            Q(correct__gt=0) | Q(wrong__gt=0)
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

    @classmethod
    def get_details(cls, league, season=None):
        season = season or league.current_season
        prefs = league.preferences()

        def keyfn(rs):
            return (rs.correct, -rs.points_delta, rs.weeks_played)

        stats = [cls(p, league) for p in prefs]
        by_user = {
            entry.user: entry for entry in sorted_standings(stats, key=keyfn)
        }

        stats = [cls(p, league, season) for p in prefs]
        return [
            (e, by_user[e.user]) for e in sorted_standings(stats, key=keyfn)
        ]
