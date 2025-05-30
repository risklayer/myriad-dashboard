from django.contrib import admin
from django.urls import path, include

from . import views

app_name = "dashboard"

urlpatterns = [
  path("", views.index, name="home"),
  path("admin/", admin.site.urls),
  path("data/", include("data.api")),
  path("shared/", include("shared.urls")),
  path("curve_explorer/", include("curve_explorer.urls")),
  path("exposure_at_risk/", include("exposure_at_risk.urls")),
  path("vulnerability_index_editor/", include("vulnerability_index_editor.urls")),
  path("scenario_calculator/", include("scenario_calculator.urls")),
  path("showcase/", include("showcase.urls")),
  path("mrr_observatory/", include("mrr_observatory.urls")),
  path("__reload__/", include("django_browser_reload.urls")),
]
