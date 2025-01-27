from django.contrib import admin
from django.urls import path, include

from . import views

app_name = "dashboard"

urlpatterns = [
  path("", views.index, name="home"),
  path("admin/", admin.site.urls),
  path("data/", include("data.urls")),
]
