from django.urls import path

from . import views

# URL namespace
app_name = "mrr_observatory"

urlpatterns = [
  path("", views.index, name="index"),
]
