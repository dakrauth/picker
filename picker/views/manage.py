from django import http
from django.urls import reverse
from django.contrib import messages
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, get_list_or_404
from django.contrib.auth.mixins import UserPassesTestMixin

from .base import PickerViewBase, SimpleFormMixin, PlayoffContext
from .. import forms
from ..models import Game, PickerResultException

__all__ = [
    'ManagementHome', 'ManageSeason', 'ManageWeek', 'ManageGame',
    'ManagePlayoffBuilder', 'ManagePlayoffs'
]


class ManagementMixin(UserPassesTestMixin):

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_active and user.is_superuser


class ManagementViewBase(ManagementMixin, PickerViewBase):

    def get_context_data(self, **kwargs):
        return super().get_context_data(management=True, **kwargs)


class ManagementHome(ManagementViewBase):
    template_name = '@manage/home.html'

    def extra_data(self, data):
        league = self.league
        data['week'] = league.current_gameset  # or PlayoffContext.week(league.playoff)


class ManageSeason(ManagementViewBase):
    template_name = '@manage/season.html'

    def extra_data(self, data):
        data['weeks'] = get_list_or_404(self.league.game_set, season=self.season)


class ManageWeek(ManagementViewBase):
    template_name = '@manage/weekly_results.html'

    @property
    def gameset(self):
        season = self.season
        week = self.args[0]
        return get_object_or_404(self.league.game_set, season=season, week=week)

    def redirect_game_set(self, gs):
        return http.HttpResponseRedirect(
            reverse('picker-game-sequence', args=(self.league.lower, gs.season, gs.week))
        )

    def post(self, *args, **kwargs):
        gs = self.gameset
        request = self.request
        if 'kickoff' in request.POST:
            gs.picks_kickoff()
            try:
                gs.update_results()
            except PickerResultException:
                pass

            messages.success(request, 'Week kickoff successful')
            return self.redirect_game_set(gs)

        if 'reminder' in request.POST:
            self.league.send_reminder_email()
            messages.success(request, 'User email sent')
            return self.redirect_game_set(gs)

        if 'update' in request.POST:
            try:
                res = gs.update_results()
            except PickerResultException as exc:
                messages.warning(request, str(exc))
            else:
                messages.success(request, '{} game(s) update'.format(res))
            return self.redirect_game_set(gs)

        form = forms.ManagementPickForm(gs, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Results saved')
            return self.redirect_game_set(gs)

        return self.render_to_response(self.get_context_data(
            form=form,
            week=gs,
            **kwargs
        ))

    def get(self, request, *args, **kwargs):
        gs = self.gameset
        if gs.has_started:
            try:
                gs.update_results()
            except PickerResultException as exc:
                messages.warning(self.request, str(exc))
            else:
                messages.success(self.request, 'Scores automatically updated!')

        return self.render_to_response(self.get_context_data(
            form=forms.ManagementPickForm(gs),
            week=gs,
            **kwargs
        ))


class ManageGame(SimpleFormMixin, ManagementViewBase):
    template_name = '@manage/game.html'
    form_class = forms.GameForm
    success_msg = 'Game saved'

    @cached_property
    def game(self):
        return get_object_or_404(Game, pk=self.args[0])

    def get(self, request, *args, **kwargs):
        game = self.game
        return self.form_handler(request, {'game': game}, instance=game)


class ManagePlayoffBuilder(SimpleFormMixin, ManagementViewBase):
    template_name = '@manage/playoff_builder.html'
    form_class = forms.PlayoffBuilderForm
    success_msg = 'Playoff saved'

    def get(self, request, *args, **kwargs):
        return self.form_handler(request, form_kws={'league': self.league})


class ManagePlayoffs(ManagementViewBase):
    template_name = '@picks/playoffs.html'

    @cached_property
    def playoff(self):
        return get_object_or_404(self.league.playoff_set, season=self.args[0])

    def post(self, request, *args, **kwargs):
        picks = self.playoff.admin
        picks.picks = {k: v for k, v in self.request.POST.items()}
        picks.save()
        return self.redirect('picker-playoffs-results', self.args[0])

    def get(self, request, *args, **kwargs):
        return self.render_to_response(
            PlayoffContext.conference(self.playoff, None, management=True)
        )
