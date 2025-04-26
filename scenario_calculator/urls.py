from django.urls import path

from . import views

# URL namespace
app_name = "scenario_calculator"

urlpatterns = [
  path("", views.index, name="index"),
  path("refine_events_form", views.refine_events_form, name="refine_events_form"),
  path("event_details/<key>", views.event_details, name="event_details"),
  path("probability/refine", views.probability_refine, name="probability_refine"),
  path("probability/result", views.probability_result, name="probability_result"),
]
