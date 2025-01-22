from django.urls import path

from . import api_static
from . import api

urlpatterns = [
  path("api/v1/", api_static.api_index, name="index"),
  path("api/v1/openapi.yaml", api_static.api_openapi_yaml, name="openapi_yaml"),
  path("api/v1/countries", api.api_countries, name="api_countries"),
  path("api/v1/nuts2areas", api.api_nuts2areas, name="api_nuts2areas"),
  path("api/v1/columns", api.api_columns, name="api_columns"),
  path("api/v1/values", api.api_values, name="api_values"),
]
