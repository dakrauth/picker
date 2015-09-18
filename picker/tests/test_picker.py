import os
from datetime import datetime
from django.test import TestCase
from django.utils.module_loading import import_string
from picker.models import *

#===============================================================================
class PickerTestCase(TestCase):

    CURRENT_SEASON = os.environ.get('CURRENT_SEASON', datetime.now().year)
    
    
#===============================================================================
class SeasonCreationTestCase(PickerTestCase):

    fixtures = ['nfl_teams.json']

    #---------------------------------------------------------------------------
    def test_create_season(self):
        season = import_string('picker.tests.games{}.season'.format(self.CURRENT_SEASON))
        lg = League.get()
        lg.create_season(**season)
        self.assertEqual(256, Game.objects.filter(week__league=lg).count())
