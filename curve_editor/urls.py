from django.urls import path

from . import views

# URL namespace
app_name = "curve_editor"

urlpatterns = [
  path("", views.index, name="index"),
  path("filter_curves", views.filter_curves, name="filter_curves"),
  path("show_curve", views.show_curve, name="show_curve"),
  path("pin", views.pin_curve, name="pin_curve"),
  path("unpin", views.unpin_curve, name="unpin_curve"),
]
