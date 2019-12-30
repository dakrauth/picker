from django.conf.urls import include, url
from .. import views

management_urls = [
    url(r'^$', views.ManagementHome.as_view(), name='picker-manage'),
    url(r'^game/(\d+)/$', views.ManageGame.as_view(), name='picker-manage-game'),
    url(r'^(?P<season>\d{4})/', include([
        url(r'^$', views.ManageSeason.as_view(), name='picker-manage-season'),
        url(r'^(-?\d+)/$', views.ManageWeek.as_view(), name='picker-manage-week'),
    ])),
]

picks_urls = [
    url(r'^$', views.Picks.as_view(), name='picker-picks'),
    url(r'^(?P<season>\d{4})/', include([
        url(r'^$', views.PicksBySeason.as_view(), name='picker-season-picks'),
        url(r'^(-?\d+)/$', views.PicksByGameset.as_view(), name='picker-picks-sequence'),
    ])),
]

results_urls = [
    url(r'^$', views.Results.as_view(), name='picker-results'),
    url(r'^(?P<season>\d{4})/', include([
        url(r'^$', views.ResultsBySeason.as_view(), name='picker-season-results'),
        url(r'^(-?\d+)/$', views.ResultsByWeek.as_view(), name='picker-game-sequence'),
    ])),
]

roster_urls = [
    url(r'^$', views.RosterRedirect.as_view(), name='picker-roster-base'),
    url(r'^(\d+)/', include([
        url(r'^$', views.Roster.as_view(), name='picker-roster'),
        url(r'^(\d{4})/$', views.Roster.as_view(), name='picker-season-roster'),
        url(r'^p/(\w+)/$', views.RosterProfile.as_view(), name='picker-roster-profile'),
    ])),
]

