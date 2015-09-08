from optparse import make_option
from django.core.management.base import BaseCommand
from picker.models import League


#===============================================================================
class Command(BaseCommand):
    help = 'Perform current game week updates'

    #---------------------------------------------------------------------------
    def handle(self, *args, **options):
        league = League.objects.get(abbr='nfl')
        week = league.current_week
        week.update_results() if week else 'Dunno'
