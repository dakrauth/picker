from django.dispatch import Signal

picker_weekly_results = Signal(providing_args=['week', 'send_mail'])
picker_confirmation = Signal(providing_args=['weekly_picks', 'auto_pick'])
picker_reminder = Signal(providing_args=['week'])
