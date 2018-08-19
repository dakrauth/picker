import os
import pytest
from django.urls import reverse
from picker import models as picker
from picker import utils


@pytest.mark.django_db
class TestViews:

    def test_lookup(self, client, quidditch):
        league, grouping, users = quidditch
        user = users[-1]
        # /<league>/picks/    picker.views.picks.Picks    picker-picks
        url = reverse('picker-picks', args=['hq'])
        r = client.get(url)
        assert r.status_code == 302
        assert r.url == reverse('login') + '?next=' + url

        utils.datetime_now('2018-06-07T00:20Z')
        client.force_login(user)
        r = client.get(url, follow=False)
        assert r.status_code == 302
        assert r.url == '/hq/picks/2018/1/'

    def test_views(self, client, quidditch):
        league, grouping, users = quidditch
        user = users[-1]
        for code in [302, 200]:
            if code == 200:
                client.force_login(user)

            for name, args in [
                # /<league>/picks/<season>/ picker.views.picks.PicksBySeason picker-season-picks
                ('picker-season-picks', ['hq', '2018']),

                # /<league>/picks/<season>/<var>/ picker.views.picks.PicksByWeek  picker-picks-sequence
                ('picker-picks-sequence', ['hq', '2018', '1']),

                # /<league>/results/  picker.views.picks.Results  picker-results
                ('picker-results', ['hq']),

                # /<league>/results/<season>/ picker.views.picks.ResultsBySeason  picker-season-results
                ('picker-season-results', ['hq', '2018']),

                # /<league>/results/<season>/<var>/ picker.views.picks.ResultsByWeek picker-game-sequence
                ('picker-game-sequence', ['hq', '2018', '1']),
            ]:
                url = reverse(name, args=args)
                r = client.get(url)
                assert r.status_code == code
                if code == 302:
                    assert r.url == reverse('login') + '?next=' + url



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
