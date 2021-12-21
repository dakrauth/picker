from django.conf import settings
from pprint import pformat


def demo_middleware(get_response):
    results = []
    DEMO = getattr(settings, 'DEMO', {})

    def middleware(request):
        fake_datetime = DEMO.get('fake_datetime')
        if fake_datetime:
            pass

        if DEMO.get('dump_post_data'):
            if request.method == 'POST' and request.path != '/accounts/login/':
                data = request.POST.dict()
                data.pop('csrfmiddlewaretoken', None)
                result = {
                    'request.user': request.user.id if request.user else None,
                    'post': data,
                    'url': request.path
                }
                results.append(result)
                print('{sep}\n{data}\n{sep}'.format(
                    sep='-' * 40,
                    data=pformat(results)
                ))
        return get_response(request)
    return middleware
