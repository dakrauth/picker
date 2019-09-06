import os
from datetime import datetime
import pytest
from django.urls import reverse
from django.utils import timezone
from django.utils.module_loading import import_string

import picker
from picker import utils, conf
from picker.templatetags import picker_tags

class TestMisc:

    def test_version(self):
        ver = picker.get_version()
        assert isinstance(ver, str)
        assert tuple(int(i) for i in ver.split('.')) == picker.VERSION


@pytest.mark.django_db
class TestAdmin:

    def test_landing(self, client, superuser, league, gamesets):
        client.force_login(superuser)
        r = client.get('/admin/')
        assert r.status_code == 200

        for part in ['conference', 'division', 'gameset', 'league', 'pickset', 'preference', 'team']:
            print(part, 'part')
            r = client.get('/admin/picker/{}/'.format(part))
            assert r.status_code == 200

            print('add')
            r = client.get('/admin/picker/{}/add/'.format(part))
            assert r.status_code == 200


def can_participate(user, gs):
    return gs


class TestUtils:

    def test_participate(self):
        conf.picker_settings['PARTICIPATION_HOOKS'] = ['tests.test_misc.can_participate']
        assert True == utils.can_user_participate(None, True)
        assert False == utils.can_user_participate(None, False)

    def test_get_templates(self):
        assert utils.get_templates('foo.html') == 'foo.html'
        assert utils.get_templates('@foo.html') == [
            'picker/foo.html', 'picker/_base/foo.html'
        ]

    def test_valid_email(self):
        assert utils.is_valid_email('foo@example.com')
        assert utils.is_valid_email('foo') == False

    def test_datetime_now(self):
        td = utils.datetime_now() - timezone.now()
        assert abs(td.total_seconds()) < 2

        when = utils.datetime_now('1991-10-31T23:00Z')
        assert when.replace(tzinfo=None) == datetime(1991, 10,31, 23)

        td = utils.datetime_now('reset') - timezone.now()
        assert abs(td.total_seconds()) < 2

        when = timezone.make_aware(datetime(2001, 1, 1))
        assert utils.parse_datetime('2001-01-01T00:00') == when
