from django import http
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404, get_list_or_404
from django.contrib.auth.mixins import UserPassesTestMixin

from ..models import League, RosterStats, Preference, PickerResultException
from .base import (
    SimplePickerViewBase, PickerViewBase, PlayoffPicksMixin, PicksBase,
    redirect_reverse
)

# Public views

def api_v1(request, action, league=None):
    league = League.get(league)
    if action == 'scores':
        return http.JsonResponse(league.scores(not league.current_gameset))

    raise http.Http404


class Home(SimplePickerViewBase):
    template_name = '@home.html'


class Team(SimplePickerViewBase):
    template_name = '@teams/detail.html'

    def extra_data(self, data):
        data['team'] = get_object_or_404(self.league.team_set, abbr=self.args[0])


class Teams(SimplePickerViewBase):
    template_name = '@teams/listing.html'


class Schedule(SimplePickerViewBase):
    template_name = '@schedule/season.html'

    def extra_data(self, data):
        data['weeks'] = get_list_or_404(self.league.game_set.select_related())


# Views requiring login


class Roster(PickerViewBase):
    template_name = '@roster/season.html'

    def extra_data(self, data):
        league = self.league
        season = int(self.args[0]) if self.args else league.current_season
        roster = RosterStats.get_details(league, season)
        data.update(season=season, roster=roster)


class RosterProfile(PickerViewBase):
    template_name = '@roster/picker.html'

    def extra_data(self, data):
        league = self.league
        username = self.args[0]
        pref = get_object_or_404(Preference, league=league, user__username=username)
        seasons = list(league.available_seasons) + [None]
        data.update(
            profile=pref,
            stats=[RosterStats(pref, league, s) for s in seasons]
        )


#  Results

class Results(PickerViewBase):
    template_name = '@unavailable.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        league = self.league
        gs = league.current_gameset
        if gs:
            if gs.has_started:
                try:
                    gs.update_results()
                except PickerResultException:
                    pass

            self.template_name = '@results/week.html'
            context['week'] = gs

        playoff = league.current_playoffs
        if playoff:
            ctx = PlayoffContext.week(playoff)
            self.template_name = '@results/playoffs.html'
            context.update(week=ctx, playoff=playoff)

        context['heading'] = 'Results currently unavailable'
        return self.render_to_response(context)


class ResultsBySeason(PickerViewBase):
    template_name = '@results/season.html'

    def extra_data(self, data):
        season = self.args[0]
        data.update(season=season, weeks=self.league.game_set.filter(season=season))


class ResultsByWeek(PickerViewBase):
    template_name = '@results/week.html'

    def extra_data(self, data):
        season, week = self.args
        data['week'] = get_object_or_404(self.league.game_set, season=season, week=week)


class ResultsForPlayoffs(PlayoffPicksMixin, PickerViewBase):

    def get(self, request, *args, **kwargs):
        return self.playoff_picks(
            request,
            get_object_or_404(self.league.playoff_set, season=self.args[0])
        )


#  Picks

class PicksBySeason(PickerViewBase):
    template_name = '@picks/season.html'

    def extra_data(self, data):
        data['weeks'] = [
            (week, week.pick_for_user(self.request.user))
            for week in get_list_or_404(self.league.game_set, season=self.args[0])
        ]


class Picks(PicksBase):

    def get(self, request, *args, **kwargs):
        week = self.league.current_gameset
        if week:
            return self.weekly_picks(request, week)

        playoff = self.league.current_playoffs
        if playoff:
            return self.playoff_picks(request, playoff)

        return super().get(request, heading='Picks currently unavailable')


class PicksByWeek(PicksBase):

    def get(self, request, *args, **kwargs):
        season, week = self.args
        week = get_object_or_404(self.league.game_set, season=season, week=week)
        return self.weekly_picks(request, week)


class PicksForPlayoffs(PicksBase):

    def get(self, request, *args, **kwargs):
        playoff = self.league.current_playoffs
        if playoff:
            return self.playoff_picks(request, playoff)

        return super().get(request, heading='Playoff picks currently unavailable')

