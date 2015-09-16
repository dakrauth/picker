from django.contrib import admin
from . import models as picker


#===============================================================================
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbr', 'is_pickable')


#===============================================================================
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'nickname', 'league', 'conference', 'division')
    list_filter = ('league', )


admin.site.register(picker.Team, TeamAdmin)
admin.site.register(picker.League, LeagueAdmin)
