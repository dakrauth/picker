import os
import sys

from freezegun import freeze_time


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)
sys.path.append(os.path.dirname(BASE_DIR))

SECRET_KEY = "@$n=(b+ih211@e02_kup2i26e)o4ovt6ureh@xbkfz!&@b(hh*"
DEBUG = True
ALLOWED_HOSTS = []
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_bootstrap5",
    "django_extensions",
    "picker.apps.PickerConfig",
    "demo",
)


MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "demo/templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "demo.context_processors.demo",
            ],
        },
    }
]

WSGI_APPLICATION = "demo.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DEMO_DB_NAME", os.path.join(BASE_DIR, "db.sqlite3")),
    }
}

SITE_ID = 1
ROOT_URLCONF = "demo.urls"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS = (os.path.join(PROJECT_DIR, "static"),)

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(PROJECT_DIR, "media")


DEMO = {"dump_post_data": True}

PICKER = {
    "FAKE_DATETIME_NOW": None,
    "NFL": {
        "TEAM_PICKER_WIDGET": "demo.forms.TemplateTeamChoice",
    },
    "HQ": {
        "TEAM_PICKER_WIDGET": "demo.forms.TemplateTeamChoice",
    },
}


freezer = freeze_time("2024-10-01 12:00:01")
freezer.start()
