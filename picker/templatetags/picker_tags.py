from hashlib import md5
from django.template import Library
from ..conf import get_setting
from ..models import PickerFavorite
from ..utils import is_valid_email, get_templates

register = Library()
GRAVATAR_BASE_URL = 'http://www.gravatar.com/avatar/'
GRAVATAR_KINDS = get_setting('GRAVATAR_KINDS')


@register.filter
def picker_user_image(user, size=None):
    if not is_valid_email(user.email):
        return ''

    return '{}{}.jpg?d={}{}'.format(
        GRAVATAR_BASE_URL,
        md5(user.email.strip().lower().encode()).hexdigest(),
        GRAVATAR_KINDS[user.id % len(GRAVATAR_KINDS)],
        '&s={}'.format(size) if size else ''
    )


@register.inclusion_tag(get_templates('@season_nav.html'), takes_context=True)
def season_nav(context, week, relative_to):
    user = context['user']
    league = context['league']
    return {
        'week': week,
        'show_playoffs': league.config('PLAYOFFS'),
        'relative_to': relative_to,
        'user': context['user'],
        'league': league,
        'is_manager': user.is_superuser or user.is_staff,
        'season_weeks': league.season_weeks(week.season if week else None)
    }


@register.inclusion_tag(get_templates('@season_nav_all.html'), takes_context=True)
def all_seasons_nav(context, current, league, relative_to):
    user = context['user']
    return {
        'label': 'All seasons',
        'current': int(current) if current else None,
        'relative_to': relative_to,
        'user': user,
        'is_manager': user.is_superuser or user.is_staff,
        'league': league
    }


@register.simple_tag(takes_context=True)
def favorite_team(context, user, league=None):
    league = league or context['league']
    try:
        return PickerFavorite.objects.get(user=user, league=league).team
    except PickerFavorite.DoesNotExist:
        pass
