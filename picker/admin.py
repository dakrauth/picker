from django import forms
from django.contrib import admin
from . import models as picker

#===============================================================================
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbr', 'is_pickable')


#===============================================================================
class AliasInline(admin.TabularInline):
    model = picker.Alias


#===============================================================================
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'nickname', 'league', 'conference', 'division')
    list_filter = ('league',)
    inlines = [AliasInline]


#===============================================================================
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbr', 'league')
    list_filter = ('league',)


#===============================================================================
class DivisionAdmin(admin.ModelAdmin):
    list_display = ('name', 'conference', 'league')
    list_filter = ('conference', 'conference__league')

    #---------------------------------------------------------------------------
    def league(self, obj):
        return obj.conference.league


#===============================================================================
class GameSetForm(forms.ModelForm):
    
    #===========================================================================
    class Meta:
        model = picker.GameSet
        fields = '__all__'
        
    #---------------------------------------------------------------------------
    def __init__(self, *args, **kws):
        super(GameSetForm, self).__init__(*args, **kws)
        if self.instance and self.instance.id:
            self.fields['byes'].queryset = self.instance.league.team_set.all()


#===============================================================================
class InlineGameForm(forms.ModelForm):
    
    #===========================================================================
    class Meta:
        model = picker.Game
        fields = '__all__'
    
    #---------------------------------------------------------------------------
    def has_add_permission(self):
        return False

    #---------------------------------------------------------------------------
    def has_change_permission(self):
        return False


#===============================================================================
class GameInline(admin.TabularInline):
    model = picker.Game
    form = InlineGameForm

    #---------------------------------------------------------------------------
    def has_add_permission(self, request):
        return False


#===============================================================================
class GameSetAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'league', 'points', 'opens', 'closes')
    list_filter = ('league', 'season')
    filter_horizontal = ['byes']
    inlines = [GameInline]
    form = GameSetForm


#===============================================================================
class PreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'league', 'status')
    list_filter = ('league', 'user')


admin.site.register(picker.Team, TeamAdmin)
admin.site.register(picker.League, LeagueAdmin)
admin.site.register(picker.Conference, ConferenceAdmin)
admin.site.register(picker.Division, DivisionAdmin)
admin.site.register(picker.GameSet, GameSetAdmin)
admin.site.register(picker.Preference, PreferenceAdmin)