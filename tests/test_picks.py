import os
import pytest
from django.urls import reverse
from picker import models as picker
from picker import (
    forms,
    stats,
    urls,
    views,
)


@pytest.mark.django_db
class TestViews:

    def test_views(self, client, league, gamesets, users):
        user = users[-1]

        for code in [302, 200]:
            if code == 200:
                client.force_login(user)

            # /<league>/picks/    picker.views.picks.Picks    picker-picks
            r = client.get(reverse('picker-picks', args=['nfl']))
            assert r.status_code == code

            # /<league>/picks/<season>/   picker.views.picks.PicksBySeason    picker-season-picks
            r = client.get(reverse('picker-season-picks', args=['nfl', '2018']))
            assert r.status_code == code

            # /<league>/picks/<season>/<var>/ picker.views.picks.PicksByWeek  picker-picks-sequence
            r = client.get(reverse('picker-picks-sequence', args=['nfl', '2018', '1']))
            assert r.status_code == code

            # /<league>/results/  picker.views.picks.Results  picker-results
            r = client.get(reverse('picker-results', args=['nfl']))
            assert r.status_code == code

            # /<league>/results/<season>/ picker.views.picks.ResultsBySeason  picker-season-results
            r = client.get(reverse('picker-season-results', args=['nfl', '2018']))
            assert r.status_code == code

            # /<league>/results/<season>/<var>/   picker.views.picks.ResultsByWeek picker-game-sequence
            r = client.get(reverse('picker-game-sequence', args=['nfl', '2018', '1']))
            assert r.status_code == code


@pytest.mark.django_db
class TestPicks:

    def test_picks(self, client, quidditch):
        league, grouping, users = quidditch
        team_dict = league.team_dict()

        user = users[0]
        assert user.picksets.count() == 0

        client.force_login(user)
        r = client.post(
            reverse('picker-picks-sequence', args=[league.slug, '2018', '1']),
            {'points': '137', 'game_1': '1', 'game_2': '3'}
        )
        assert r.status_code == 302
        assert user.picksets.count() == 1

        ps = user.picksets.get()
        assert ps.points == 137

        gp = ps.gamepick_set.first()
        assert gp.winner.id == 1

        user = users[1]
        client.force_login(user)
        r = client.post(
            reverse('picker-picks-sequence', args=[league.slug, '2018', '1']),
            {'points': '731', 'game_1': '2', 'game_2': '4'}
        )
        assert r.status_code == 302
        assert user.picksets.count() == 1

        ps = user.picksets.get()
        assert ps.points == 731

        gp = ps.gamepick_set.first()
        assert gp.winner.id == 2

        assert picker.PickSet.objects.count() == 2
