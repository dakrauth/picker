from django.conf import settings
from django.urls import include, re_path
from django.contrib import admin
from . import views

urlpatterns = [
    re_path(r"^$", views.home, name="demo-home"),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^accounts/", include("django.contrib.auth.urls")),
    re_path(r"^(?P<league>\w+)/", include("picker.urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, show_indexes=True
    )
