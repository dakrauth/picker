import os
import pytest
from django.urls import reverse
from django.core.management import call_command

from picker import models as picker
from picker import (
    forms,
    stats,
    urls,
    utils,
    views,
    signals,
    managers,
)
from picker.templatetags import picker_tags
from picker.management.commands import import_league, import_season


@pytest.mark.django_db
class TestLeague:

    def test_management_commands(self):
        call_command('import_league', 'tests/nfl2018.json')
        call_command('import_season', 'tests/nfl2018.json')

    def test_import(self, nfl_data):
        league, teams = picker.League.import_league(nfl_data['league'])
        assert league == picker.League.objects.pickable()[0]

        assert league.slug == 'nfl'
        assert league.abbr == 'NFL'
        assert league.current_season == 2018
        assert league.conferences.count() == 2
        print(picker.Division.objects.all())
        #assert picker.Division.objects.count() == 8
        assert league.teams.count() == 32

        info = league.import_season(nfl_data['season'])
        assert len(info) == 17
        for gs, is_new, games in info:
            assert is_new == True
            assert all(is_new for g, is_new in games)
        assert picker.Game.objects.incomplete().count() == 256

        assert picker.Alias.objects.count() == 4
        td = league.team_dict()
        assert td['WAS'] == td['WSH']

    def test_config(self, league):
        assert league.config('TEAM_PICKER_WIDGET') == 'demo.forms.TemplateTeamChoice'

    def test_team(self, league):
        tm = picker.Team.objects.get(league=league, nickname='Jaguars')
        aliases = list(tm.aliases.values_list('name', flat=True))
        assert aliases == ['JAC']

        assert tm.season_points() == 0
        assert tm.complete_record() == [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

    def test_league(self, league, gamesets):
        assert league.current_playoffs == None
        assert league.latest_gameset == None


@pytest.mark.django_db
class TestUsersPrefsGroups:

    def test_users(self, users):
        assert len(users) == 10
        assert users[0].is_superuser
        assert not any(u.is_superuser for u in users[1:])
        assert picker.Preference.objects.count() == 10
        assert picker.Preference.objects.active().count() == 10

    def test_group(self, league, users):
        users_dct = {u.id: u for u in users}
        group = league.pickergrouping_set.get()

        assert users_dct == {
            mbr.user.id: mbr.user
            for mbr in group.members.all()
        }

    def test_favs(self, league, user):
        fav = picker.PickerFavorite.objects.create(user=user, league=league, team=None)
        assert str(fav) == '{}: {} ({})'.format(user, 'None', league)
        fav.team = league.team_dict()['SEA']
        fav.save()
        assert str(fav) == '{}: {} ({})'.format(user, 'Seattle Seahawks', league)

        pref = picker.Preference.objects.get(user=user)
        form = forms.PreferenceForm(pref, {
            'nfl_favorite': league.team_dict()['CLE'].id,
            'autopick': picker.Preference.Autopick.NONE
        })

        is_valid =  form.is_valid()
        if not is_valid:
            print(form.errors)

        assert is_valid
        form.save()
        fav = picker.PickerFavorite.objects.get(user=user, league=league)
        assert fav.team.abbr == 'CLE'


@pytest.mark.django_db
class TestBasicViews:

    def test_anon_views(self, client, league, gamesets):
        # /<league>/teams/    picker.views.picks.Teams    picker-teams
        r = client.get(reverse('picker-teams', args=['nfl']))
        assert r.status_code == 200

        # /<league>/teams/<var>/  picker.views.picks.Team picker-team
        r = client.get(reverse('picker-team', args=['nfl', 'SEA']))
        assert r.status_code == 200

        # /<league>/schedule/ picker.views.picks.Schedule picker-schedule
        r = client.get(reverse('picker-schedule', args=['nfl']))
        assert r.status_code == 200

        # /<league>/schedule/<season>/    picker.views.picks.Schedule picker-schedule-year
        r = client.get(reverse('picker-schedule-year', args=['nfl', '2018']))
        assert r.status_code == 200
