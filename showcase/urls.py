from django.urls import path

from . import views

# URL namespace
app_name = "showcase"

urlpatterns = [
  path("", views.index, name="index"),
  # path("refine_form", views.refine_form, name="refine_form"),
  path("showcase_details", views.showcase_details, name="showcase_details"),
]
