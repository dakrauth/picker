from django.dispatch import Signal

picker_confirmation = Signal(providing_args=['pickset', 'auto_pick'])
