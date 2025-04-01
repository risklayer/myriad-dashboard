from django.urls import path

from . import views

# URL namespace
app_name = "shared"

urlpatterns = [
  path("pin/<pin_type>", views.pin, name="pin"),
  path("unpin/<pin_type>", views.unpin, name="unpin"),
]
