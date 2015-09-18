from django.db import models
from django.utils.module_loading import import_string

#from delivery.delivery import send_mail

from .conf import get_setting
from .utils import datetime_now

send_mail = import_string(get_setting('EMAIL_HANDLER'))

#===============================================================================
class LeagueManager(models.Manager):
    
    use_for_related_fields = True
    
    #---------------------------------------------------------------------------
    def pickable(self, **kws):
        return self.filter(is_pickable=True, **kws)


#===============================================================================
class GamePickManager(models.Manager):

    use_for_related_fields = True
    
    #---------------------------------------------------------------------------
    def games_started(self):
        return self.filter(game__kickoff__lte=datetime_now())


#===============================================================================
class GameManager(models.Manager):

    use_for_related_fields = True
    
    #---------------------------------------------------------------------------
    def games_started(self):
        return self.filter(kickoff__lte=datetime_now())

    #---------------------------------------------------------------------------
    def incomplete(self, **kws):
        kws['status'] = self.model.Status.UNPLAYED
        return self.filter(**kws)


#===============================================================================
class PreferenceManager(models.Manager):
    
    #---------------------------------------------------------------------------
    def active(self, **kws):
        return self.filter(
            status=self.model.Status.ACTIVE,
            user__is_active=True,
            **kws
        )
        
    #---------------------------------------------------------------------------
    def email_active(self, subject, body, html=''):
        self.email(
            subject,
            body, 
            selected=self.active(),
            html=html,
        )

    #---------------------------------------------------------------------------
    def email(self, subject, body, selected, html=''):
        send_mail(
            subject, 
            body, 
            from_email=settings.SERVER_EMAIL,
            recipient_list=[p.pretty_email for p in selected],
            html=html,
        )

