from django import forms
from django.utils.module_loading import import_string

from . import models as picker
from . import utils
from .signals import picker_results

_picker_widget = None
game_key_format = 'game_{}'.format


def get_picker_widget(league):
    global _picker_widget
    if not _picker_widget:
        widget_path = league.config('TEAM_PICKER_WIDGET')
        if widget_path:
            _picker_widget = import_string(widget_path)

        _picker_widget = _picker_widget or forms.RadioSelect

    return _picker_widget


class GameField(forms.ChoiceField):

    def __init__(self, game, manage=False, widget=None):
        choices = ((str(game.away.id), game.away), (str(game.home.id), game.home))
        self.game = game
        self.manage = manage
        self.game_id = game.id
        self.is_game = True
        self.disabled = not self.manage and (self.game.start_time <= utils.datetime_now())
        super(GameField, self).__init__(
            choices=choices,
            label=game.start_time.strftime('%a, %b %d %I:%M %p'),
            required=False,
            help_text=game.tv,
            widget=widget or get_picker_widget(game.week.league)
        )

    def widget_attrs(self, widget):
        return {'readonly': 'readonly', 'disabled': 'disabled'} if self.disabled else {}


class FieldIter:

    def __init__(self, form):
        self.fields = []
        self.form = form

    def append(self, name):
        self.fields.append(name)

    def __iter__(self):
        for name in self.fields:
            yield self.form[name]


class BasePickForm(forms.Form):

    management = False

    def __init__(self, week, *args, **kws):
        super(BasePickForm, self).__init__(*args, **kws)
        self.week = week
        self.game_fields = FieldIter(self)
        games = list(week.game_set.all())
        for gm in games:
            key = game_key_format(gm.id)
            self.fields[key] = GameField(gm, self.management)
            self.game_fields.append(key)

        if games:
            self.fields['points'] = forms.IntegerField(
                label='{} {}'.format('Points Total:', games[-1].vs_description),
                required=False
            )


class ManagementPickForm(BasePickForm):

    management = True

    def __init__(self, week, *args, **kws):
        kws.setdefault('initial', self.get_initial_picks(week))
        super(ManagementPickForm, self).__init__(week, *args, **kws)
        self.fields['send_mail'] = forms.BooleanField(required=False)

    def save(self):
        week = self.week
        data = self.cleaned_data.copy()
        send_mail = data.pop('send_mail', False)
        week.points = data.pop('points', 0)
        week.save()
        team_dict = week.league.team_dict()

        for key, winner in data.items():
            if winner:
                key = key.split('_')[1]
                game = week.game_set.get(pk=key)
                game.winner = team_dict[int(winner)]

        week.update_pick_status()
        picker_results.send(sender=week.__class__, week=week, send_mail=send_mail)

    @staticmethod
    def get_initial_picks(week):
        return dict({
            game_key_format(game.id): game.winner.id
            for game in week.game_set.all()
            if game.winner
        }, points=week.points)


class UserPickForm(BasePickForm):

    def __init__(self, user, week, *args, **kws):
        kws.setdefault('initial', self.get_initial_user_picks(week, user))
        self.user = user
        super(UserPickForm, self).__init__(week, *args, **kws)

    def save(self):
        data = self.cleaned_data.copy()
        week = self.week
        picks = week.pick_set.get_or_create(user=self.user)[0]
        picks.points = data.pop('points', 0) or 0
        picks.strategy = picker.PickSet.Strategy.USER
        picks.save()

        games_dict = {game_key_format(g.id): g for g in week.games}
        game_picks = [(k, v) for k, v in data.items() if v]
        for game, winner in game_picks:
            game = games_dict.get(game, None)
            if not game:
                continue

            gp, created = picks.gamepick_set.get_or_create(
                game=game,
                defaults=dict(winner=None)
            )
            if not game.has_started:
                gp.winner_id = winner
                gp.save()

        picks.send_confirmation()
        picks.complete_picks(False, games_dict.values())
        return week

    @staticmethod
    def get_initial_user_picks(week, user):
        wp = week.pick_for_user(user)
        if not wp:
            return {}

        return dict({
            game_key_format(gp.game.id): gp.winner.id
            for gp in wp.gamepick_set.filter(winner__isnull=False)
        }, points=wp.points)


class GameForm(forms.ModelForm):

    class Meta:
        model = picker.Game
        fields = ('start_time', 'location')


class PlayoffField(forms.ModelChoiceField):

    def __init__(self, conf, seed):
        super(PlayoffField, self).__init__(
            label='%s %d Seed' % (conf, seed),
            queryset=conf.team_set.all(),
            required=False
        )
        self.conf = conf
        self.seed = seed


class PlayoffBuilderForm(forms.ModelForm):

    NUM_TEAMS = 6

    class Meta:
        model = picker.Playoff
        fields = ('kickoff', )

    def __init__(self, league, *args, **kws):
        self.league = league
        if 'instance' not in kws:
            kws['instance'] = picker.Playoff.objects.get_or_create(
                league=league,
                season=league.current_season,
                defaults={'kickoff': utils.datetime_now()}
            )[0]

        super(PlayoffBuilderForm, self).__init__(*args, **kws)
        for conf in league.conference_set.all():
            for seed in range(1, self.NUM_TEAMS + 1):
                field_name = '{}_{}'.format(conf.abbr, seed)
                self.fields[field_name] = PlayoffField(conf, seed)

        if self.instance.id:
            for playoff_team in self.instance.playoffteam_set.all():
                key = '%s_%s' % (playoff_team.team.conference, playoff_team.seed)
                self.fields[key].initial = playoff_team.team

    def save(self, commit=True):
        super(PlayoffBuilderForm, self).save()
        playoff = self.instance
        data = self.cleaned_data
        data.pop('kickoff')

        picker.PlayoffTeam.objects.filter(playoff=playoff).delete()
        for key, team in data.items():
            if team:
                seed = key.split('_')[-1]
                playoff.playoffteam_set.create(team=team, seed=seed)

        return playoff


class PreferenceForm(forms.ModelForm):

    class Meta:
        model = picker.Preference
        fields = ('autopick',)

    def __init__(self, instance, *args, **kws):
        kws['instance'] = instance
        self.current_email = instance.user.email.lower()
        kws.setdefault('initial', {})['email'] = self.current_email
        super(PreferenceForm, self).__init__(*args, **kws)

        for league in picker.League.objects.all():
            field_name = '{}_favorite'.format(league.slug)
            current = None
            if instance:
                try:
                    current = picker.PickerFavorite.objects.get(user=instance.user, league=league)
                except picker.PickerFavorite.DoesNotExist:
                    pass

            self.fields[field_name] = forms.ModelChoiceField(
                picker.Team.objects.filter(league=league),
                label='{} Fav'.format(league.abbr.upper()),
                empty_label='-- Select --',
                required=False,
                initial=current.team if current else None
            )

    def save(self, commit=True):
        super(PreferenceForm, self).save(commit)
        if commit:
            picker.PickerFavorite.objects.filter(user=self.instance.user).delete()
            for key in self.cleaned_data:
                if not key.endswith('_favorite'):
                    continue

                slug = key.rsplit('_')[0]
                league = picker.League.objects.get(slug=slug)
                picker.PickerFavorite.objects.create(
                    league=league,
                    user=self.instance.user,
                    team=self.cleaned_data[key]
                )
