from django.conf.urls import include, url
from .. import views
from . import picks, sports

urlpatterns = [
    url(r'^$', views.Home.as_view(), name='picker-home'),
    url(r'^teams/', include(sports.teams_urls)),
    url(r'^schedule/', include(sports.schedule_urls)),
    url(r'^roster/', include(picks.roster_urls)),
    url(r'^results/', include(picks.results_urls)),
    url(r'^picks/', include(picks.picks_urls)),
    url(r'^manage/', include(picks.management_urls))
]
