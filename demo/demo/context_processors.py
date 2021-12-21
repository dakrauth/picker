from django.conf import settings


def demo(request):
    DEMO = getattr(settings, 'DEMO', {})
    return {
        'fake_datetime': DEMO.get('allow_fake_datetime')
    }
