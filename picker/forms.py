from datetime import datetime

from django import forms
from django.template import Template, Context
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.utils.encoding import force_unicode
from django.contrib import messages

from . import models as picker
from . import utils
from .signals import picker_weekly_results
import markdown2


game_key_format = 'game_{}'.format
team_choice_label_format = u'''<label class="team-choice {home_away}" for="{choice_id}">
    <input type="radio" id="{choice_id}" {readonly} {disabled} value="{value}" name="{name}" {checked}>
    <div class="team-info team-{team.abbr_lower}">
        <span class="market">{team.market}</span>
        <span class="nickname">{team.nickname}</span>
        <span class="record">{team.record_as_string}</span>
    </div>
</label>'''.format

team_choice_template = u'''<label class="team-choice {{ home_away }}" for="{{ choice_id }}">
    <input type="radio" id="{{ choice_id }}" {{ readonly }} {{ disabled }} value="{{ value }}" name="{{ name }}" {{ checked }}>
    <div class="team-info team-{{ team.abbr.lower }}">
        <span class="market">{{ team.market }}</span>
        <span class="nickname">{{ team.nickname }}</span>
        <span class="record">{{ team.record_as_string }}</span>
    </div>
</label>'''


#-------------------------------------------------------------------------------
def user_email_exists(email):
    try:
        User.objects.get(email=email)
    except User.DoesNotExist:
        False
    else:
        return True


#===============================================================================
class TeamChoiceRadioSelect(forms.RadioSelect):
    
    #---------------------------------------------------------------------------
    def render(self, name, value, attrs=None):
        str_value = force_unicode(value if value is not None else '')
        final_attrs = self.build_attrs(attrs)

        labels = ''
        for i, (game_id, team) in enumerate(self.choices):
            readonly = bool('readonly' in final_attrs)
            labels += team_choice_label_format(
                home_away='home' if i else 'away',
                choice_id='%s_%s' % (attrs['id'], game_id),
                name=name,
                team=team,
                checked='checked="checked"' if game_id == str_value else '',
                value=game_id,
                readonly='readonly="readonly"' if readonly else '',
                disabled='disabled="disabled"' if readonly else ''
            )
            
        return mark_safe(labels)


#===============================================================================
class TemplateTeamChoice(forms.RadioSelect):
    
    #---------------------------------------------------------------------------
    def __init__(self, *args, **kws):
        super(TemplateTeamChoice, self).__init__(*args, **kws)
        self.template = self.load_template()
    
    #---------------------------------------------------------------------------
    @staticmethod
    def load_template():
        return Template(team_choice_template)
    
    #---------------------------------------------------------------------------
    def render(self, name, value, attrs=None):
        str_value = force_unicode(value if value is not None else '')
        final_attrs = self.build_attrs(attrs)
        labels = ''
        for i, (game_id, team) in enumerate(self.choices):
            readonly = bool('readonly' in final_attrs)
            labels += self.template.render(Context(dict(
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

    widget = TemplateTeamChoice

    #---------------------------------------------------------------------------
    def __init__(self, game, manage=False):
        choices = ((str(game.away.id), game.away), (str(game.home.id), game.home))
        self.game = game
        self.manage = manage
        self.game_id = game.id
        self.is_game = True
        self.disabled = not self.manage and (self.game.kickoff <= datetime.now())
        super(GameField, self).__init__(
            choices=choices,
            label=game.kickoff.strftime('%a, %b %d %I:%M %p'),
            required=False,
            help_text=game.tv
        )

    #---------------------------------------------------------------------------
    def widget_attrs(self, widget):
        if self.disabled:
            return {'readonly': 'readonly', 'disabled': 'disabled'}
        
        return {}


#-------------------------------------------------------------------------------
def get_initial_picks(week):
    results = {
        game_key_format(game.id): game.winner.id
        for game in week.game_set.all()
        if game.winner
    }
    results['points'] = week.points
    return results


#-------------------------------------------------------------------------------
def get_initial_user_picks(week, user):
    wp = week.pick_for_user(user)
    if not wp:
        return {}
    
    return dict({
        game_key_format(gp.game.id): gp.winner.id
        for gp in wp.gamepick_set.filter(winner__isnull=False)
    }, points=wp.points)


#===============================================================================
class BasePickForm(forms.Form):
    
    management = False
    
    #---------------------------------------------------------------------------
    def __init__(self, week, *args, **kws):
        super(BasePickForm, self).__init__(*args, **kws)
        self.week = week
        for gm in week.game_set.all():
            key = game_key_format(gm.id)
            self.fields[key] = GameField(gm, self.management)

        self.fields['points'] = forms.IntegerField(label=gm.vs_description, required=False)


#===============================================================================
class ManagementPickForm(BasePickForm):

    management = True
    
    #---------------------------------------------------------------------------
    def __init__(self, week, *args, **kws):
        kws.setdefault('initial', get_initial_picks(week))
        super(ManagementPickForm, self).__init__(week, *args, **kws)
    
    #---------------------------------------------------------------------------
    def save(self):
        data = self.cleaned_data.copy()
        week = self.week
        points = data.pop('points', 0)
        
        week.points = points
        week.save()
        
        for key, winner in data.items():
            if winner:
                key = key.split('_')[1]
                game = week.game_set.get(pk=key)
                game.winner_id = winner
                game.save()
        
        week.update_pick_status()
        if points:
            summary = picker.WeekSummary.objects.summarize_for_week(week)
            if summary and data.pop('send_mail', False):
                picker_weekly_results.send(sender=picker.WeekSummary, summary=summary)


#===============================================================================
class UserPickForm(BasePickForm):
    
    #---------------------------------------------------------------------------
    def __init__(self, user, week, *args, **kws):
        kws.setdefault('initial', get_initial_user_picks(week, user))
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
                defaults={'kickoff': datetime.now()}
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
        exclude = ('user', 'status', 'autopick')
    
    #---------------------------------------------------------------------------
    def __init__(self, instance, *args, **kws):
        kws['instance'] = instance
        self.current_email = instance.user.email.lower()
        kws.setdefault('initial', {})['email'] = self.current_email
        super(PreferenceForm, self).__init__(*args, **kws)
        
    #---------------------------------------------------------------------------
    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if email != self.current_email and user_email_exists(email):
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
