from django.urls import path

from . import views

# URL namespace
app_name = "boilerplate"

urlpatterns = [
  path("", views.index, name="index"),
]
