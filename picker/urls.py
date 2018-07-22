from django.conf import settings
from django.conf.urls import include, url
from . import views

management_urls = [
    url(r'^$', views.ManagementHome.as_view(), name='picker-manage'),
    url(r'^game/(\d+)/$', views.ManageGame.as_view(), name='picker-manage-game'),
    url(r'^(\d{4})/$', views.ManageSeason.as_view(), name='picker-manage-season'),
    url(r'^(\d{4})/(-?\d+)/$', views.ManageWeek.as_view(), name='picker-manage-week'),
    url(r'^(\d{4})/(playoffs)/$', views.ManagePlayoffs.as_view(), name='picker-manage-week'),
    url(
        r'^playoff-builder/$',
        views.ManagePlayoffBuilder.as_view(),
        name='picker-manage-playoff-builder'
    )
]

picks_urls = [
    url(r'^$', views.Picks.as_view(), name='picker-picks'),
    url(r'^(\d{4})/$', views.PicksBySeason.as_view(), name='picker-season-picks'),
    url(r'^(\d{4})/(-?\d+)/$', views.PicksByWeek.as_view(), name='picker-picks-sequence'),
    url(r'^(\d{4})/playoffs/$', views.PicksForPlayoffs.as_view(), name='picker-playoffs-picks'),
]

results_urls = [
    url(r'^$', views.Results.as_view(), name='picker-results'),
    url(r'^(\d{4})/$', views.ResultsBySeason.as_view(), name='picker-season-results'),
    url(r'^(\d{4})/(-?\d+)/$', views.ResultsByWeek.as_view(), name='picker-game-sequence'),
    url(r'^(\d{4})/playoffs/$', views.ResultsForPlayoffs.as_view(), name='picker-playoffs-results'),
]

roster_urls = [
    url(r'^$', views.Roster.as_view(), name='picker-roster'),
    url(r'^(?P<season>20\d\d)/$', views.Roster.as_view(), name='picker-season-roster'),
    url(r'^p/(\w+)/$', views.RosterProfile.as_view(), name='picker-roster-profile'),
]

teams_urls = [
    url(r'^$', views.Teams.as_view(), name='picker-teams'),
    url(r'^(\w+)/$', views.Team.as_view(), name='picker-team'),
]

schedule_urls = [
    url(r'^$', views.Schedule.as_view(), name='picker-schedule'),
    url(r'^(\d{4})$', views.Schedule.as_view(), name='picker-schedule-year'),
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

if settings.DEBUG:
    from django.views.static import serve
    urlpatterns += [url(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}
    )]
