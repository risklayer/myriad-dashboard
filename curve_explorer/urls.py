from django.urls import path

from . import views

# URL namespace
app_name = "curve_explorer"

urlpatterns = [
  path("", views.index, name="index"),
  path("filter_curves", views.filter_curves, name="filter_curves"),
  path("show_curve", views.show_curve, name="show_curve"),
]
