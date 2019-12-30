from django.conf.urls import url
from ..views import sports as views


teams_urls = [
    url(r'^$', views.Teams.as_view(), name='picker-teams'),
    url(r'^([\w&-]+)/$', views.Team.as_view(), name='picker-team'),
]

schedule_urls = [
    url(r'^$', views.Schedule.as_view(), name='picker-schedule'),
    url(r'^(?P<season>\d{4})/$', views.Schedule.as_view(), name='picker-schedule-year'),
]

