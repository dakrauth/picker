from django.dispatch import Signal

picker_results = Signal(providing_args=['gameset', 'send_mail'])
picker_confirmation = Signal(providing_args=['pickset', 'auto_pick'])
picker_reminder = Signal(providing_args=['gameset'])
