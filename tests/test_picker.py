import os
import pytest
from django.urls import reverse
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
from picker.league.nfl import scores
from picker.management.commands import import_league, import_season

def filepath_here(name):
    return os.path.join(os.path.dirname(__file__), name)


@pytest.mark.django_db
class TestLeague:

    def test_import(self, nfl_json_path, nfl_season_json_path):
        league, teams = picker.League.import_league(nfl_json_path)
        assert league.slug == 'nfl'
        assert league.abbr == 'NFL'
        assert league.current_season == 2018
        assert league.team_set.count() == 32

        new_old = league.import_season(nfl_season_json_path)
        assert new_old == [256, 0]

        assert picker.Alias.objects.count() == 4
        td = league.team_dict()
        assert td['WAS'] == td['WSH']

    def test_config(self, league):
        assert league.config('TEAM_PICKER_WIDGET') == 'demo.forms.TemplateTeamChoice'


@pytest.mark.django_db
class TestUsersPrefsGroups:

    def test_users(self, users):
        assert len(users) == 10
        assert users[0].is_superuser
        assert not any(u.is_superuser for u in users[1:])
        assert picker.Preference.objects.count() == 10

    def test_group(self, league, users):
        users_dct = {u.id: u for u in users}
        group = league.pickergrouping_set.get()

        assert users_dct == {
            mbr.user.id: mbr.user
            for mbr in group.members.all()
        }

# /<league>/manage/   picker.views.manage.ManagementHome  picker-manage
# /<league>/manage/<season>/  picker.views.manage.ManageSeason    picker-manage-season
# /<league>/manage/<season>/<var>/    picker.views.manage.ManagePlayoffs  picker-manage-week
# /<league>/manage/<season>/<var>/    picker.views.manage.ManageWeek  picker-manage-week
# /<league>/manage/game/<var>/    picker.views.manage.ManageGame  picker-manage-game
# /<league>/manage/playoff-builder/   picker.views.manage.ManagePlayoffBuilder    picker-manage-playoff-builder

# /<league>/picks/    picker.views.picks.Picks    picker-picks
# /<league>/picks/<season>/   picker.views.picks.PicksBySeason    picker-season-picks
# /<league>/picks/<season>/<var>/ picker.views.picks.PicksByWeek  picker-picks-sequence
# /<league>/picks/<season>/playoffs/  picker.views.picks.PicksForPlayoffs picker-playoffs-picks

# /<league>/results/  picker.views.picks.Results  picker-results
# /<league>/results/<season>/ picker.views.picks.ResultsBySeason  picker-season-results
# /<league>/results/<season>/<var>/   picker.views.picks.ResultsByWeek    picker-game-sequence
# /<league>/results/<season>/playoffs/    picker.views.picks.ResultsForPlayoffs   picker-playoffs-results

# /<league>/roster/   picker.views.picks.RosterRedirect   picker-roster-base
# /<league>/roster/<var>/ picker.views.picks.Roster   picker-roster
# /<league>/roster/<var>/<season>/    picker.views.picks.Roster   picker-season-roster
# /<league>/roster/<var>/p/<league>/roster/(\d+)/p/<var>/ picker.views.picks.RosterProfile    picker-roster-profile


@pytest.mark.django_db
class TestViews:

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

