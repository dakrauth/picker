
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
        user = users[0]

        for code in [302, 200]:
            if code == 200:
                client.force_login(user)

            # /<league>/manage/   picker.views.manage.ManagementHome  picker-manage
            r = client.get(reverse('picker-manage', args=['hq']))
            assert r.status_code == code

            # /<league>/manage/<season>/  picker.views.manage.ManageSeason    picker-manage-season
            r = client.get(reverse('picker-manage-season', args=['hq', league.current_season]))
            assert r.status_code == code

            # /<league>/manage/<season>/<var>/    picker.views.manage.ManageWeek  picker-manage-week
            r = client.get(reverse('picker-manage-week', args=['hq', league.current_season, '1']))
            assert r.status_code == code

            # /<league>/manage/game/<var>/    picker.views.manage.ManageGame  picker-manage-game
            r = client.get(reverse('picker-manage-game', args=['hq', '1']))
            assert r.status_code == code

