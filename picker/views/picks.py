from django import http
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, get_list_or_404

from .. import forms
from ..stats import RosterStats
from .playoffs import PlayoffContext
from .base import SimplePickerViewBase, PickerViewBase, SimpleFormMixin
from ..models import League, Preference, PickerResultException, PickerGrouping

# Public views

class Home(SimplePickerViewBase):
    template_name = '@home.html'


class Team(SimplePickerViewBase):
    template_name = '@teams/detail.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            team=get_object_or_404(self.league.teams, abbr=self.args[0]),
            **kwargs
        )


class Teams(SimplePickerViewBase):
    template_name = '@teams/listing.html'


class Schedule(SimplePickerViewBase):
    template_name = '@schedule/season.html'

    def get_context_data(self, **kwargs):
        season = self.season or self.league.latest_season
        return super().get_context_data(
            gamesets=get_list_or_404(
                self.league.gamesets.filter(season=self.season).select_related()
            ),
            **kwargs
        )


# Views requiring login

class RosterRedirect(PickerViewBase):
    template_name = '@roster/select.html'

    def get(self, request, *args, **kwargs):
        qs = request.user.picker_memberships.filter(
            group__leagues=self.league
        ).select_related('group')

        count = qs.count()
        if count == 1:
            mbr = qs[0]
            return self.redirect('picker-roster', self.league.slug, mbr.group.id)
        elif count > 1:
            return self.render_to_response({
                'memberships': qs
            })

        self.template_name = '@unavailable.html'
        return self.render_to_response({
            'league_base': 'picker/base.html',
            'heading': 'Roster unavailable',
            'description': 'Please check back later',
        })


class RosterMixin:

    @property
    def group(self):
        return get_object_or_404(PickerGrouping, pk=self.args[0])


class Roster(RosterMixin, PickerViewBase):
    template_name = '@roster/season.html'

    @property
    def season(self):
        if len(self.args) == 2:
            return int(self.args[1])

        return super().season

    def get_context_data(self, **kwargs):
        group = self.group
        roster = RosterStats.get_details(self.league, group, self.season)
        return super().get_context_data(
            roster=roster,
            group=group,
            other_groups=PickerGrouping.objects.filter(members__user=self.request.user),
            **kwargs
        )


class RosterProfile(RosterMixin, PickerViewBase):
    template_name = '@roster/picker.html'

    def get_context_data(self, **kwargs):
        league = self.league
        username = self.args[1]
        pref = get_object_or_404(Preference, user__username=username)
        seasons = list(league.available_seasons) + [None]
        return super().get_context_data(
            profile=pref,
            stats=[RosterStats(pref, league, s) for s in seasons],
            **kwargs
        )


#  Results

class Results(PickerViewBase):
    template_name = '@results/results.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        league = self.league
        gameset = league.current_gameset
        if gameset:
            if gameset.has_started:
                try:
                    gameset.update_results(gameset.get_results())
                except PickerResultException:
                    pass
        elif self.league.config('PLAYOFFS'):
            playoff = league.current_playoffs
            if playoff:
                ctx = PlayoffContext.week(playoff)
                self.template_name = '@results/playoffs.html'
                context.update(gameset=ctx, playoff=playoff)
                return self.render_to_response(context)

        gameset = gameset or self.league.latest_gameset
        if gameset:
            context['gameset'] = gameset
        else:
            self.template_name = '@unavailable.html'
            context['heading'] = 'Results currently unavailable'

        return self.render_to_response(context)


class ResultsBySeason(PickerViewBase):
    template_name = '@results/season.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            gamesets=self.league.gamesets.filter(season=self.season), **kwargs
        )


class ResultsByWeek(PickerViewBase):
    template_name = '@results/results.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(gameset=get_object_or_404(
            self.league.gamesets,
            season=self.season,
            sequence=self.args[0]
        ), **kwargs)


#  Picks

class PicksBySeason(PickerViewBase):
    template_name = '@picks/season.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(gamesets=[
            (gs, gs.pick_for_user(self.request.user))
            for gs in get_list_or_404(self.league.gamesets, season=self.season)
        ], **kwargs)


class Picks(PickerViewBase):
    template_name = '@unavailable.html'

    def get(self, request, *args, **kwargs):
        league = self.league
        gameset = league.current_gameset or league.latest_gameset
        if gameset:
            return self.redirect(
                'picker-picks-sequence',
                league.slug,
                gameset.season,
                gameset.sequence
            )

        if league.config('PLAYOFFS'):
            playoff = league.current_playoffs
            if playoff:
                return self.redirect('picker-playoffs-picks', league.slug, self.season)

        return self.render_to_response(self.get_context_data(
            heading='Picks currently unavailable',
            **kwargs
        ))


class PicksByGameset(SimpleFormMixin, PickerViewBase):
    success_msg = 'Your picks have been saved'
    form_class = forms.UserPickForm

    @cached_property
    def gameset(self):
        return get_object_or_404(
            self.league.gamesets,
            season=self.season,
            sequence=self.args[0]
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(user=self.request.user, gameset=self.gameset)
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(gameset=self.gameset, **kwargs)

    def get(self, request, *args, **kwargs):
        gameset = self.gameset
        if gameset.is_open:
            self.template_name = '@picks/make.html'
            return self.render_to_response(self.get_context_data(**kwargs))

        self.template_name = '@picks/show.html'
        return self.render_to_response(self.get_context_data(
            picks=gameset.pick_for_user(self.request.user),
            **kwargs
        ))
