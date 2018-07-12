from django.db import models
from django.utils.module_loading import import_string

from .conf import get_setting
from .utils import datetime_now

send_mail = import_string(get_setting('EMAIL_HANDLER'))


class LeagueManager(models.Manager):

    def pickable(self, **kws):
        return self.filter(is_pickable=True, **kws)


class GamePickManager(models.Manager):

    def games_started(self):
        return self.filter(game__kickoff__lte=datetime_now())


class GameManager(models.Manager):

    def games_started(self):
        return self.filter(kickoff__lte=datetime_now())

    def incomplete(self, **kws):
        kws['status'] = self.model.Status.UNPLAYED
        return self.filter(**kws)


class PreferenceManager(models.Manager):

    def active(self, **kws):
        return self.filter(
            status=self.model.Status.ACTIVE,
            user__is_active=True,
            **kws
        )

    def email_active(self, subject, body, html=''):
        self.email(
            subject,
            body,
            selected=self.active(),
            html=html,
        )

    def email(self, subject, body, selected, html=''):
        send_mail(
            subject,
            body,
            from_email=settings.SERVER_EMAIL,
            recipient_list=[p.pretty_email for p in selected],
            html=html,
        )


class PickSetManager(models.Manager):

    def create_for_user(self, user, gs, strategy, games=None, send_confirmation=True):
        Strategy = self.model.Strategy
        is_auto = (strategy == Strategy.RANDOM)
        wp = gs.pick_set.create(
            user=user,
            points=gs.league.random_points() if is_auto else 0,
            strategy=strategy
        )
        wp.complete_picks(is_auto, games or gs.game_set.all())
        if send_confirmation:
            wp.send_confirmation(is_auto)

        return wp
