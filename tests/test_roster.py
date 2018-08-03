
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

    def test_roster(self, client, league, gamesets, users):
        client.force_login(users[1])

        # /<league>/roster/ picker.views.picks.RosterRedirect   picker-roster-base
        r = client.get(reverse('picker-roster-base', args=['nfl']))
        assert r.status_code == 302


    def test_views(self, client, league, gamesets, users):
        user = users[1]

        for code in [302, 200]:
            if code == 200:
                client.force_login(user)

            # /<league>/roster/<var>/ picker.views.picks.Roster   picker-roster
            r = client.get(reverse('picker-roster', args=['nfl', '1']))
            assert r.status_code == code

            # /<league>/roster/<var>/<season>/    picker.views.picks.Roster   picker-season-roster
            r = client.get(reverse('picker-season-roster', args=['nfl', '1', '2018']))
            assert r.status_code == code

            # /<league>/roster/<var>/p/<var>/ picker.views.picks.RosterProfile    picker-roster-profile
            r = client.get(reverse('picker-roster-profile', args=['nfl', '1', user.username]))
            assert r.status_code == code
