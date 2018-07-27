from datetime import date
from django.conf import settings
from django.utils.module_loading import import_string

today = date.today()
season = today.year if today.month > 6 else today.year - 1

DEFAULT_PICKER_SETTINGS = {
    'DEFAULT_LEAGUE': 'nfl',
    'EMAIL_HANDLER': 'django.core.mail.send_mail',
    'FAKE_DATETIME_NOW': False,
    'FBS_CURRENT_SEASON': season,
    'FCS_CURRENT_SEASON': season,
    'LEAGUE_MODULE_BASE': 'picker.league',
    'LOGOS_UPLOAD_DIR': 'picker/logos',
    'NAIA_CURRENT_SEASON': season,

    'NFL_CURRENT_SEASON': season,
    'NFL_FORCE_AUTOPICK': True,
    'NFL_FEED_URL': 'http://www.nfl.com/rss/rsslanding?searchString=home',
    'NFL_PLAYOFFS': False,
    'NFL_PLAYOFF_SCORE': {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 2, 10: 2, 11: 4},

    'PARTICIPATION_HOOKS': [],
    'TEAM_PICKER_WIDGET': None,
}

picker_settings = dict(
    DEFAULT_PICKER_SETTINGS,
    **getattr(settings, 'PICKER', {})
)

get_setting = picker_settings.get


def import_setting(key, default=None):
    value = get_setting(key)
    if not value:
        return default

    return import_string(value)
