from datetime import datetime
from optparse import make_option
from django.core.management.base import BaseCommand
from picker.models import League

#===============================================================================
class Command(BaseCommand):
    help = 'Send out reminders'

    #---------------------------------------------------------------------------
    def handle(self, *args, **options):
        if args:
            arg = [int(i) for i in args[0].split('-')]
            today = datetime(*arg).date()
        else:
            today = datetime.now().date()
        
        #TODO
        league = League.objects.get(abbr='nfl')
        gw = league.current_week
        first_game = gw.first_game
        
        if first_game.kickoff.date() == today:
            league.send_reminder_email()
            print 'Week {}, game 1: {}:{}'.format(first_game.week, today, first_game)
            
        else:
            print '%s:N/A' % today
