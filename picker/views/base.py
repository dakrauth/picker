from django import http
from django.urls import reverse
from django.contrib import messages
from django.views.generic import TemplateView
from django.utils.functional import cached_property
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.mixins import LoginRequiredMixin

from .. import utils
from .. import forms
from ..models import League, Preference


class PlayoffContext:

    @staticmethod
    def week(playoff):
        count = 1 + playoff.league.game_set.count()
        weeks = [{'season': playoff.season, 'week': w} for w in range(1, count)]
        return {'season_weeks': weeks, 'week': 'playoffs'}

    @staticmethod
    def conference(playoff, user, **kws):
        teams = {}
        confs = {
            abbr: []
            for abbr in playoff.league.conference_set.values_list('abbr', flat=True)
        }
        for seed, team in playoff.seeds:
            conf = confs[team.conference.abbr]
            conf.append(team.abbr)
            teams[team.abbr] = {
                'url': team.logo.url if team.logo else '',
                'seed': seed,
                'name': team.name,
                'abbr': team.abbr,
                'record': team.record_as_string,
                'conf': team.conference.abbr
            }

        try:
            picks = playoff.playoffpicks_set.get(user=user)
        except ObjectDoesNotExist:
            picks = None

        return dict(
            {key: utils.json_dumps(confs[key]) for key in confs},
            teams=utils.json_dumps(teams),
            picks=utils.json_dumps(picks.picks if picks else []),
            week=PlayoffContext.week(playoff),
            **kws
        )


class PlayoffPicksMixin:

    def playoff_picks(self, request, playoff):
        season = self.season
        if utils.datetime_now() > playoff.kickoff:
            return self.redirect('picker-playoffs-results', self.league.slug, season)

        if request.method == 'POST':
            picks = playoff.user_picks(request.user)
            picks.picks = {k: v for k, v in request.POST.items()}
            picks.save()
            return self.redirect('picker-playoffs-results', self.league.slug, season)

        self.template_name = '@picks/playoffs.html'
        return self.render_to_response(PlayoffContext.conference(playoff, request.user))


class SimpleFormMixin:
    form_class = None
    success_msg = None
    redirect_path = None

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def form_handler(
        self,
        request,
        context=None,
        instance=None,
        form_kws=None,
    ):
        form_kws = form_kws or {}
        if instance:
            form_kws['instance'] = instance

        if request.method == 'POST':
            form = self.form_class(data=request.POST, **form_kws)
            if form.is_valid():
                form.save()
                if self.success_msg:
                    messages.success(request, self.success_msg)

                return http.HttpResponseRedirect(self.redirect_path or request.path)
        else:
            form = self.form_class(**form_kws)

        return self.render_to_response(self.get_context_data(
            form=form,
            **(context or {})
        ))


class SimplePickerViewBase(TemplateView):

    @staticmethod
    def redirect(name, *args, **kwargs):
        return http.HttpResponseRedirect(reverse(name, args=args, kwargs=kwargs))

    @property
    def season(self):
        season = self.kwargs.get('season')
        if season and season.isdigit():
            return int(season)

        league = self.league
        current_season = league.current_season
        return season if season else self.league.current_season

    @cached_property
    def league(self):
        return League.get(self.kwargs['league'])

    def get_template_names(self):
        if self.template_name is None:
            raise ImproperlyConfigured(
                "TemplateResponseMixin requires either a definition of "
                "'template_name' or an implementation of 'get_template_names()'"
            )

        return utils.get_templates(self.template_name, self.league)

    def extra_data(self, data):
        pass

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        league = self.league
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            try:
                data['preferences'] = Preference.objects.get(user=self.request.user)
            except Preference.DoesNotExist:
                pass

        data.update({
            'now': utils.datetime_now(),
            'league': league,
            'season': self.season or league.current_season,
            'league_base': 'picker/{}/base.html'.format(league.slug)
        })
        self.extra_data(data)
        return data

    def render_to_response(self, context, **response_kwargs):
        response_kwargs.setdefault('content_type', self.content_type)
        template_names = self.get_template_names()
        context['template_names'] = template_names
        return self.response_class(
            request=self.request,
            template=template_names,
            context=context,
            using=self.template_engine,
            **response_kwargs
        )



class WeeklyPicksMixin(PlayoffPicksMixin, SimpleFormMixin):
    success_msg = 'Your picks have been saved'
    form_class = forms.UserPickForm

    def weekly_picks(self, request, week):
        if week.is_open:
            data = {'user': request.user, 'week': week}
            self.template_name = '@picks/make.html'
            self.redirect_path = week.get_absolute_url()
            return self.form_handler(request, context=data, form_kws=data)

        self.template_name = '@picks/show.html'
        picks = week.pick_for_user(request.user)
        return super().get(request, week=week, picks=picks)


class PickerViewBase(LoginRequiredMixin, SimplePickerViewBase):
    pass


class PicksBase(WeeklyPicksMixin, PickerViewBase):
    template_name = '@unavailable.html'
