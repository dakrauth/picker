import os
import pytest
from django.urls import reverse
from django.utils.module_loading import import_string

from picker import models as picker
from picker import utils, conf


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


def can_participate(pref, gs):
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
