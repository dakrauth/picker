from django.db.models import Q
from django.core.cache import cache
from django.contrib.auth import get_user_model
from .models import GameSet
from .utils import sorted_standings


def percent(num, denom):
    return 0.0 if denom == 0 else num / denom * 100.0


class RosterStats:

    def __init__(self, user, league, season=None):
        self.user = user
        self.season = season
        self.league = league
        self.correct = 0
        self.wrong = 0
        self.points_delta = 0

        queryset = self.user.picksets.filter(gameset__league=league).select_related().filter(
            Q(correct__gt=0) | Q(wrong__gt=0)
        )

        if season:
            queryset = queryset.filter(gameset__season=season)

        self.picksets_played = 0
        for picks in queryset.select_related('gameset'):
            self.picksets_played += 1
            self.correct += picks.correct
            self.wrong += picks.wrong
            self.points_delta += picks.points_delta if picks.gameset.points else 0

        self.is_active = self.user.is_active
        self.pct = percent(self.correct, self.correct + self.wrong)
        self.avg_points_delta = (
            self.points_delta / self.picksets_played
            if self.picksets_played
            else 0
        )

        query = GameSet.objects.filter(picksets__is_winner=True, picksets__user=self.user)
        if self.season:
            query = query.filter(season=self.season)

        self.picksets_won = query.count() # list(query.select_related())

    def __str__(self):
        return '{}{}'.format(self.user, ' ({})'.format(self.season) if self.season else '')

    __repr__ = __str__

    @classmethod
    def get_details(cls, league, group, season=None):
        key = 'roster-stats:{}:{}'.format(league.id, group.id)
        season = season or league.current_season
        #mbrs = group.members.all().select_related('user')
        User = get_user_model()
        users = User.objects.filter(picker_memberships__group=group)

        def keyfn(rs):
            return (rs.correct, -rs.points_delta, rs.picksets_played)

        stats = [cls(u, league) for u in users]
        by_user = {
            entry.user: entry for entry in sorted_standings(stats, key=keyfn)
        }

        stats = [cls(u, league, season) for u in users]
        results = [
            (e, by_user[e.user]) for e in sorted_standings(stats, key=keyfn)
        ]
        return results

