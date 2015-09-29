from datetime import date
from django.conf import settings
from django.utils.module_loading import import_string

today = date.today()
season = today.year if today.month > 6 else today.year - 1

DEFAULT_PICKER_SETTINGS = {
    'NFL_FEED_URL': 'http://www.nfl.com/rss/rsslanding?searchString=home',
    'FAKE_DATETIME_NOW': False,
    'FOOTBALL_FORCE_AUTOPICK': True,
    'NFL_PLAYOFF_SCORE': {1:1, 2:1, 3:1, 4:1, 5:1, 6:1, 7:1, 8:1, 9:2, 10:2, 11:4},
    'NFL_CURRENT_SEASON': season,
    'FBS_CURRENT_SEASON': season,
    'FCS_CURRENT_SEASON': season,
    'NAIA_CURRENT_SEASON': season,
    'DEFAULT_LEAGUE': 'nfl',
    'LEAGUE_MODULE_BASE': 'picker.league',
    'LOGOS_UPLOAD_DIR': 'picker/logos',
    'EMAIL_HANDLER': 'django.core.mail.send_mail',
    'TEAM_PICKER_WIDGET': 'picker.forms.TemplateTeamChoice',
    'PARTICIPATION_HOOKS': []
}
picker_settings = dict(
    DEFAULT_PICKER_SETTINGS,
    **getattr(settings, 'PICKER', {})
)

get_setting = picker_settings.get

#-------------------------------------------------------------------------------
def import_setting(key, default=None):
    value = get_setting(key)
    if not value:
        return default
    
    return import_string(value)