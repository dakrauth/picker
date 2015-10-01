from datetime import datetime
from django import forms
from django.template import Template, Context, loader, TemplateDoesNotExist
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.contrib import messages
from . import models as picker
from . import utils
from . import conf
from .signals import picker_weekly_results

game_key_format = 'game_{}'.format

_picker_widget = None

#-------------------------------------------------------------------------------
def get_picker_widget():
    global _picker_widget
    if not _picker_widget:
        _picker_widget = conf.import_setting('TEAM_PICKER_WIDGET') or forms.RadioSelect

    return _picker_widget


#===============================================================================
class TemplateTeamChoice(forms.RadioSelect):
    
    template_name = 'picker/team_pick_field.html'
    
    #---------------------------------------------------------------------------
    def __init__(self, *args, **kws):
        super(TemplateTeamChoice, self).__init__(*args, **kws)
    
    #---------------------------------------------------------------------------
    def render(self, name, value, attrs=None):
        try:
            tmpl = loader.get_template(self.template_name)
        except TemplateDoesNotExist:
            return super(TemplateTeamChoice, self).render(name, value, attrs)
            
        labels = ''
        str_value = force_unicode(value if value is not None else '')
        final_attrs = self.build_attrs(attrs)
        for i, (game_id, team) in enumerate(self.choices):
            readonly = bool('readonly' in final_attrs)
            labels += tmpl.render(Context(dict(
                home_away='home' if i else 'away',
                choice_id='%s_%s' % (attrs['id'], game_id),
                name=name,
                team=team,
                checked='checked="checked"' if game_id == str_value else '',
                value=game_id,
                readonly='readonly="readonly"' if readonly else '',
                disabled='disabled="disabled"' if readonly else ''
            )))
            
        return mark_safe(labels)


#===============================================================================
class GameField(forms.ChoiceField):

    #---------------------------------------------------------------------------
    def __init__(self, game, manage=False, widget=None):
        choices = ((str(game.away.id), game.away), (str(game.home.id), game.home))
        self.game = game
        self.manage = manage
        self.game_id = game.id
        self.is_game = True
        self.disabled = not self.manage and (self.game.kickoff <= utils.datetime_now())
        widget = widget or get_picker_widget()
        super(GameField, self).__init__(
            choices=choices,
            label=game.kickoff.strftime('%a, %b %d %I:%M %p'),
            required=False,
            help_text=game.tv,
            widget=widget
        )

    #---------------------------------------------------------------------------
    def widget_attrs(self, widget):
        return {
            'readonly': 'readonly',
            'disabled': 'disabled'
        } if self.disabled else {}



#===============================================================================
class FieldIter(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, form):
        self.fields = []
        self.form = form
        
    #---------------------------------------------------------------------------
    def append(self, name):
        self.fields.append(name)
    
    #---------------------------------------------------------------------------
    def __iter__(self):
        for name in self.fields:
            yield self.form[name]


#===============================================================================
class BasePickForm(forms.Form):
    
    management = False
    
    #---------------------------------------------------------------------------
    def __init__(self, week, *args, **kws):
        super(BasePickForm, self).__init__(*args, **kws)
        self.week = week
        self.game_fields = FieldIter(self)
        for gm in week.game_set.all():
            key = game_key_format(gm.id)
            self.fields[key] = GameField(gm, self.management)
            self.game_fields.append(key)

        self.fields['points'] = forms.IntegerField(
            label=gm.vs_description,
            required=False
        )


#===============================================================================
class ManagementPickForm(BasePickForm):

    management = True
    
    #---------------------------------------------------------------------------
    def __init__(self, week, *args, **kws):
        kws.setdefault('initial', self.get_initial_picks(week))
        super(ManagementPickForm, self).__init__(week, *args, **kws)
        self.fields['send_mail'] = forms.BooleanField(required=False)
    
    #---------------------------------------------------------------------------
    def save(self):
        week = self.week
        data = self.cleaned_data.copy()
        send_mail = data.pop('send_mail', False)
        week.points = data.pop('points', 0)
        week.save()
        
        for key, winner in data.items():
            if winner:
                key = key.split('_')[1]
                game = week.game_set.get(pk=key)
                game.winner_id = winner
                game.save()
        
        week.update_pick_status()
        picker_weekly_results.send(sender=week.__class__, week=week, send_mail=send_mail)

    #---------------------------------------------------------------------------
    @staticmethod
    def get_initial_picks(week):
        return dict({
            game_key_format(game.id): game.winner.id
            for game in week.game_set.all()
            if game.winner
        }, points=week.points)


#===============================================================================
class UserPickForm(BasePickForm):
    
    #---------------------------------------------------------------------------
    def __init__(self, user, week, *args, **kws):
        kws.setdefault('initial', self.get_initial_user_picks(week, user))
        self.user = user
        super(UserPickForm, self).__init__(week, *args, **kws)
    
    #---------------------------------------------------------------------------
    def save(self):
        data = self.cleaned_data.copy()
        week = self.week
        picks, created = week.pick_set.get_or_create(user=self.user)
        picks.points = data.pop('points', 0) or 0
        picks.strategy = picker.PickSet.Strategy.USER
        picks.save()

        games_dict = dict([(game_key_format(g.id), g) for g in week.games])
        game_picks = [(k, v) for k,v in data.items() if v]
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
    
    #---------------------------------------------------------------------------
    @staticmethod
    def get_initial_user_picks(week, user):
        wp = week.pick_for_user(user)
        if not wp:
            return {}

        return dict({
            game_key_format(gp.game.id): gp.winner.id
            for gp in wp.gamepick_set.filter(winner__isnull=False)
        }, points=wp.points)


#===============================================================================
class GameForm(forms.ModelForm):

    #===========================================================================
    class Meta:
        model = picker.Game
        fields = ('kickoff', 'location')


#===============================================================================
class PlayoffField(forms.ModelChoiceField):
    
    #---------------------------------------------------------------------------
    def __init__(self, conf, seed):
        super(PlayoffField, self).__init__(
            label='%s %d Seed' % (conf, seed),
            queryset=conf.team_set.all(),
            required=False
        )
        self.conf = conf
        self.seed = seed


#===============================================================================
class PlayoffBuilderForm(forms.ModelForm):
   
    NUM_TEAMS = 6
    
    #===========================================================================
    class Meta:
        model = picker.Playoff
        fields = ('kickoff', )
    
    #---------------------------------------------------------------------------
    def __init__(self, league, *args, **kws):
        self.league = league
        if 'instance' not in kws:
            kws['instance'], created = picker.Playoff.objects.get_or_create(
                league=league,
                season=league.current_season,
                defaults={'kickoff': utils.datetime_now()}
            )
            
        super(PlayoffBuilderForm, self).__init__(*args, **kws)
        for conf in league.conference_set.all():
            for seed in range(1, self.NUM_TEAMS + 1):
                field_name = '{}_{}'.format(conf.abbr, seed)
                self.fields[field_name] = PlayoffField(conf, seed)
            
        if self.instance.id:
            for playoff_team in self.instance.playoffteam_set.all():
                key = '%s_%s' % (playoff_team.team.conference, playoff_team.seed)
                self.fields[key].initial = playoff_team.team
        
    #---------------------------------------------------------------------------
    def save(self):
        super(PlayoffBuilderForm, self).save()
        playoff = self.instance
        data = self.cleaned_data
        data.pop('kickoff')
        
        picker.PlayoffTeam.objects.filter(playoff=playoff).delete()
        afc, nfc = [], []
        for key, team in data.items():
            if team:
                conf, seed = key.split('_')
                playoff.playoffteam_set.create(team=team, seed=seed)

        return playoff


#===============================================================================
class PreferenceForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(size='50')))
    favorite_team = forms.ModelChoiceField(
        picker.Team.objects.filter(league__abbr='NFL'),
        empty_label='-- Select --',
        required=False
    )
    
    #===========================================================================
    class Meta:
        model = picker.Preference
        exclude = ('user', 'status', 'autopick', 'league')
    
    #---------------------------------------------------------------------------
    def __init__(self, instance, *args, **kws):
        kws['instance'] = instance
        self.current_email = instance.user.email.lower()
        kws.setdefault('initial', {})['email'] = self.current_email
        super(PreferenceForm, self).__init__(*args, **kws)
        
    #---------------------------------------------------------------------------
    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if email != self.current_email and utils.user_email_exists(email):
            raise forms.ValidationError('That email is already in use')
            
        return email

    #---------------------------------------------------------------------------
    def save(self, commit=True):
        super(PreferenceForm, self).save(commit)
        if commit:
            email = self.cleaned_data['email']
            if email != self.current_email:
                self.instance.user.email = email
                self.instance.user.save()
