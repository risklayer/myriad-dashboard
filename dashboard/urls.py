from django.contrib import admin
from django.urls import path, include

from . import views

app_name = "dashboard"

urlpatterns = [
  path("", views.index, name="home"),
  path("admin/", admin.site.urls),
  path("data/", include("data.api")),
  path("curve_editor/", include("curve_editor.urls")),
  path("__reload__/", include("django_browser_reload.urls")),
]
