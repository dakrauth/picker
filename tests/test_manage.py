
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
            r = client.get(reverse('picker-manage', args=['nfl']))
            assert r.status_code == code

            # /<league>/manage/<season>/  picker.views.manage.ManageSeason    picker-manage-season
            r = client.get(reverse('picker-manage-season', args=['nfl', '2018']))
            assert r.status_code == code

            # /<league>/manage/<season>/<var>/    picker.views.manage.ManageWeek  picker-manage-week
            r = client.get(reverse('picker-manage-week', args=['nfl', '2018', '1']))
            assert r.status_code == code

            # /<league>/manage/game/<var>/    picker.views.manage.ManageGame  picker-manage-game
            r = client.get(reverse('picker-manage-game', args=['nfl', '1']))
            assert r.status_code == code

            # /<league>/manage/playoff-builder/   picker.views.manage.ManagePlayoffBuilder    picker-manage-playoff-builder
            r = client.get(reverse('picker-manage-playoff-builder', args=['nfl']))
            assert r.status_code == code

