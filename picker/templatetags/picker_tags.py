from hashlib import md5

from django.template import Library
from django.core.validators import ValidationError, validate_email

from ..conf import get_setting
from ..models import PickerFavorite
from ..utils import get_templates

register = Library()
GRAVATAR_BASE_URL = 'http://www.gravatar.com/avatar/'
GRAVATAR_KINDS = get_setting('GRAVATAR_KINDS')


@register.filter
def picker_user_image(user, size=None):
    try:
        validate_email(user.email)
    except ValidationError:
        return ''

    return '{}{}.jpg?d={}{}'.format(
        GRAVATAR_BASE_URL,
        md5(user.email.strip().lower().encode()).hexdigest(),
        GRAVATAR_KINDS[user.id % len(GRAVATAR_KINDS)],
        '&s={}'.format(size) if size else ''
    )


@register.simple_tag
def user_result(user_pick, actual_results):
    try:
        res = actual_results[user_pick[0]]
        if res['winner']:
            return 'correct' if res['winner'] == user_pick[1] else 'incorrect'

        return 'unknown'
    except KeyError:
        return 'error'


@register.inclusion_tag(get_templates('@season_nav.html'), takes_context=True)
def season_nav(context, gameset, relative_to):
    user = context['user']
    league = context['league']
    return {
        'gameset': gameset,
        'relative_to': relative_to,
        'user': context['user'],
        'league': league,
        'is_manager': user.is_superuser or user.is_staff,
        'season_gamesets': league.season_gamesets(gameset.season if gameset else None)
    }


@register.inclusion_tag(get_templates('@season_nav_all.html'), takes_context=True)
def all_seasons_nav(context, current, league, relative_to, group=None):
    user = context['user']
    return {
        'label': 'All seasons',
        'group': group,
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
