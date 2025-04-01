from django.urls import path

from . import views

# URL namespace
app_name = "exposure_at_risk"

urlpatterns = [
  path("", views.index, name="index"),
  path("refine_form", views.refine_form, name="refine_form"),
  path("column_details/<key>", views.column_details, name="column_details"),
]
