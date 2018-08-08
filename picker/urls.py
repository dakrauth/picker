from django.conf import settings
from django.conf.urls import include, url
from . import views
from .views import playoffs as playoff_views


management_urls = [
    url(r'^$', views.ManagementHome.as_view(), name='picker-manage'),
    url(r'^game/(\d+)/$', views.ManageGame.as_view(), name='picker-manage-game'),
    url(r'^(?P<season>\d{4})/', include([
        url(r'^$', views.ManageSeason.as_view(), name='picker-manage-season'),
        url(r'^(-?\d+)/$', views.ManageWeek.as_view(), name='picker-manage-week'),
        url(r'^(playoffs)/$', views.ManagePlayoffs.as_view(), name='picker-manage-week'),
    ])),
    url(
        r'^playoff-builder/$',
        views.ManagePlayoffBuilder.as_view(),
        name='picker-manage-playoff-builder'
    )
]

picks_urls = [
    url(r'^$', views.Picks.as_view(), name='picker-picks'),
    url(r'^(?P<season>\d{4})/', include([
        url(r'^$', views.PicksBySeason.as_view(), name='picker-season-picks'),
        url(r'^(-?\d+)/$', views.PicksByGameset.as_view(), name='picker-picks-sequence'),
        url(r'^playoffs/$', playoff_views.PicksForPlayoffs.as_view(), name='picker-playoffs-picks'),
    ])),
]

results_urls = [
    url(r'^$', views.Results.as_view(), name='picker-results'),
    url(r'^(?P<season>\d{4})/', include([
        url(r'^$', views.ResultsBySeason.as_view(), name='picker-season-results'),
        url(r'^(-?\d+)/$', views.ResultsByWeek.as_view(), name='picker-game-sequence'),
        url(r'^playoffs/$', playoff_views.ResultsForPlayoffs.as_view(), name='picker-playoffs-results'),
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

teams_urls = [
    url(r'^$', views.Teams.as_view(), name='picker-teams'),
    url(r'^(\w+)/$', views.Team.as_view(), name='picker-team'),
]

schedule_urls = [
    url(r'^$', views.Schedule.as_view(), name='picker-schedule'),
    url(r'^(?P<season>\d{4})/$', views.Schedule.as_view(), name='picker-schedule-year'),
]

urlpatterns = [
    url(r'^$', views.Home.as_view(), name='picker-home'),
    url(r'^teams/', include(teams_urls)),
    url(r'^schedule/', include(schedule_urls)),
    url(r'^roster/', include(roster_urls)),
    url(r'^results/', include(results_urls)),
    url(r'^picks/', include(picks_urls)),
    url(r'^manage/', include(management_urls))
]

