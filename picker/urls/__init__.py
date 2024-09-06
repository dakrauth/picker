from django.urls import include, re_path
from .. import views
from . import picks, sports

urlpatterns = [
    re_path(r"^$", views.Home.as_view(), name="picker-home"),
    re_path(r"^teams/", include(sports.teams_urls)),
    re_path(r"^schedule/", include(sports.schedule_urls)),
    re_path(r"^roster/", include(picks.roster_urls)),
    re_path(r"^results/", include(picks.results_urls)),
    re_path(r"^picks/", include(picks.picks_urls)),
    re_path(r"^manage/", include(picks.management_urls)),
]
