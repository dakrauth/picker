from django import http
from django.urls import reverse
from django.contrib import messages
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, get_list_or_404
from django.contrib.auth.mixins import UserPassesTestMixin

from .base import PickerViewBase, SimpleFormMixin
from .playoffs import PlayoffContext
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


    def get_context_data(self, **kwargs):
        # or PlayoffContext.week(league.playoff)
        return super().get_context_data(gameset=self.league.current_gameset, **kwargs)


class ManageSeason(ManagementViewBase):
    template_name = '@manage/season.html'

    def get_context_data(self, **kwargs):
        gamesets = get_list_or_404(self.league.gamesets, season=self.season)
        return super().get_context_data(gamesets=gamesets, **kwargs)


class ManageWeek(ManagementViewBase):
    template_name = '@manage/results.html'

    @property
    def gameset(self):
        season = self.season
        sequence = self.args[0]
        return get_object_or_404(self.league.gamesets, season=season, sequence=sequence)

    def redirect_gameset(self, gs):
        return http.HttpResponseRedirect(
            self.request.path
        )

    def get_form(self):
        return forms.ManagementPickForm

    def post(self, *args, **kwargs):
        gs = self.gameset
        request = self.request
        FormClass = self.get_form()
        form = FormClass(gs, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Results saved')
            return self.redirect_gameset(gs)

        return self.render_to_response(self.get_context_data(
            form=form,
            gameset=gs,
            **kwargs
        ))

    def get(self, request, *args, **kwargs):
        gs = self.gameset
        return self.render_to_response(self.get_context_data(
            form=forms.ManagementPickForm(gs),
            gameset=gs,
            **kwargs
        ))


class ManageGame(SimpleFormMixin, ManagementViewBase):
    template_name = '@manage/game.html'
    form_class = forms.GameForm
    success_msg = 'Game saved'

    @cached_property
    def game(self):
        return get_object_or_404(Game, pk=self.args[0])

    def get_context_data(self, **kwargs):
        return super().get_context_data(instance=self.game, **kwargs)

    def get_form_kwargs(self):
        data = super().get_form_kwargs()
        data['instance'] = self.game
        return data

class ManagePlayoffBuilder(SimpleFormMixin, ManagementViewBase):
    template_name = '@manage/playoff_builder.html'
    form_class = forms.PlayoffBuilderForm
    success_msg = 'Playoff saved'

    def get_form_kwargs(self):
        data = super().get_form_kwargs()
        data['league'] = self.league
        return data


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
