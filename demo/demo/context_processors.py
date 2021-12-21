from django.conf import settings
from picker.utils import datetime_now


def demo(request):
    return {
        'allow_fake_datetime': getattr(settings, 'DEMO', {}).get('allow_fake_datetime'),
        'is_fake_datetime': datetime_now.is_fake
    }
