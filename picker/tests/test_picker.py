import os
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils.module_loading import import_string
from picker.models import *
from picker.utils import datetime_now

#-------------------------------------------------------------------------------
def create_users(n_users):
    return [
        User.objects.create_user(
            username='user{}'.format(i),
            email='user{}@example.com'.format(i)
            password='password'
        ) for i in range(1, n_users + 1)
    ]


#===============================================================================
class PickerTestCase(TestCase):

    CURRENT_SEASON = os.environ.get('CURRENT_SEASON', datetime_now().year)
    
    
#===============================================================================
class SeasonCreationTestCase(PickerTestCase):

    fixtures = ['nfl_teams.json']

    #---------------------------------------------------------------------------
    def test_create_season(self):
        season = import_string('picker.tests.games{}.season'.format(self.CURRENT_SEASON))
        lg = League.get()
        lg.create_season(**season)
        self.assertEqual(256, Game.objects.filter(week__league=lg).count())
