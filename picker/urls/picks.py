from django.urls import include, re_path
from .. import views

management_urls = [
    re_path(r"^$", views.ManagementHome.as_view(), name="picker-manage"),
    re_path(r"^game/(\d+)/$", views.ManageGame.as_view(), name="picker-manage-game"),
    re_path(
        r"^(?P<season>\d{4})/",
        include(
            [
                re_path(r"^$", views.ManageSeason.as_view(), name="picker-manage-season"),
                re_path(r"^(-?\d+)/$", views.ManageWeek.as_view(), name="picker-manage-week"),
            ]
        ),
    ),
]

picks_urls = [
    re_path(r"^$", views.Picks.as_view(), name="picker-picks"),
    re_path(
        r"^(?P<season>\d{4})/",
        include(
            [
                re_path(r"^$", views.PicksBySeason.as_view(), name="picker-season-picks"),
                re_path(
                    r"^(-?\d+)/$",
                    views.PicksByGameset.as_view(),
                    name="picker-picks-sequence",
                ),
            ]
        ),
    ),
]

results_urls = [
    re_path(
        r"^$",
        views.GroupMembershipRedirect.as_view(redirect_view_name="picker-results-group"),
        name="picker-results",
    ),
    re_path(r"^(?P<group_id>\d)/$", views.Results.as_view(), name="picker-results-group"),
    re_path(
        r"^(?P<group_id>\d+)/(?P<season>\d{4})/",
        include(
            [
                re_path(r"^$", views.ResultsBySeason.as_view(), name="picker-season-results"),
                re_path(
                    r"^(-?\d+)/$",
                    views.ResultsByWeek.as_view(),
                    name="picker-game-sequence",
                ),
            ]
        ),
    ),
]


roster_urls = [
    re_path(
        r"^$",
        views.GroupMembershipRedirect.as_view(redirect_view_name="picker-roster"),
        name="picker-roster-base",
    ),
    re_path(
        r"^(\d+)/",
        include(
            [
                re_path(r"^$", views.Roster.as_view(), name="picker-roster"),
                re_path(r"^(\d{4})/$", views.Roster.as_view(), name="picker-season-roster"),
                re_path(
                    r"^p/(\w+)/$",
                    views.RosterProfile.as_view(),
                    name="picker-roster-profile",
                ),
            ]
        ),
    ),
]
