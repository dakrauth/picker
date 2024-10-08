from django.urls import include, re_path
from django.contrib import admin

urlpatterns = [
    re_path(r"^accounts/", include("django.contrib.auth.urls")),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^(?P<league>\w+)/", include("picker.urls")),
]
