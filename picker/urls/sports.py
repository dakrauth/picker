from django.urls import re_path
from ..views import sports as views


teams_urls = [
    re_path(r"^$", views.Teams.as_view(), name="picker-teams"),
    re_path(r"^([\w&-]+)/$", views.Team.as_view(), name="picker-team"),
]

schedule_urls = [
    re_path(r"^$", views.Schedule.as_view(), name="picker-schedule"),
    re_path(r"^(?P<season>\d{4})/$", views.Schedule.as_view(), name="picker-schedule-year"),
]
