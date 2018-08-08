from datetime import date
from django.conf import settings
from django.utils.module_loading import import_string

today = date.today()


DEFAULT_PICKER_SETTINGS = {
    'DEFAULT_LEAGUE': 'NFL',
    'EMAIL_HANDLER': 'django.core.mail.send_mail',
    'FAKE_DATETIME_NOW': False,
    'LOGOS_UPLOAD_DIR': 'picker/logos',
    'GRAVATAR_KINDS': ['identicon', 'monsterid', 'wavatar', 'retro', 'robohash'],

    'PARTICIPATION_HOOKS': [],
    'TEAM_PICKER_WIDGET': None,
    '_BASE': {
        'CURRENT_SEASON': None,
        'FORCE_AUTOPICK': True,
        'PLAYOFFS': False,
        'PLAYOFF_SCORE': {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 2, 10: 2, 11: 4},
        'PARTICIPATION_HOOKS': [],
        'TEAM_PICKER_WIDGET': None,
        'FAKE_DATETIME_NOW': False,
        'GAMESET_DURATION': {'days': 7, 'seconds': -1},
    }
}

picker_settings = dict(
    DEFAULT_PICKER_SETTINGS,
    **getattr(settings, 'PICKER', {})
)

get_setting = picker_settings.get
