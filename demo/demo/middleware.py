from django.conf import settings
from pprint import pformat
from picker.utils import datetime_now


def demo_middleware(get_response):
    results = []
    DEMO = getattr(settings, 'DEMO', {})
    def middleware(request):
        if DEMO.get('allow_fake_datetime'):
            fake_dt = request.GET.get('fakedt', None)
            if fake_dt:
                when = datetime_now(fake_dt)
                print('Using fake datetime from query string: {}'.format(when))

        if DEMO.get('dump_post_data'):
            if request.method == 'POST' and request.path != '/accounts/login/':
                data = request.POST.dict()
                data.pop('csrfmiddlewaretoken', None)
                result = {
                    'request.user': request.user.id if request.user else None,
                    'post' : data,
                    'url': request.path
                }
                results.append(result)
                print('{sep}\n{data}\n{sep}'.format(
                    sep='-' * 40,
                    data=pformat(results)
                ))
        return get_response(request)
    return middleware
