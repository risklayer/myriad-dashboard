from django.urls import path

from . import api_static
from . import api

app_name = "data"

urlpatterns = [
  path("api/v1/", api_static.api_index, name="index"),
  path("api/v1/openapi.yaml", api_static.api_openapi_yaml, name="openapi_yaml"),
  path("api/v1/countries", api.api_countries, name="api_countries"),
  path("api/v1/nuts2areas", api.api_nuts2areas, name="api_nuts2areas"),
  path("api/v1/nuts2shapes", api.api_nuts2shapes, name="api_nuts2shapes"),
  path("api/v1/nuts2shape/<str:nuts2_key>/values", api.api_nuts2shape_values, name="api_nuts2shape_values"),
  path("api/v1/column/hazard", api.api_column_hazard, name="api_column_hazard"),
  path("api/v1/column/exposure", api.api_column_exposure, name="api_column_exposure"),
  path("api/v1/column/threshold", api.api_column_threshold, name="api_column_threshold"),
  path(
    "api/v1/column/return_period", api.api_column_return_period, name="api_column_return_period"
  ),
  path("api/v1/columns", api.api_columns, name="api_columns"),
  path("api/v1/values", api.api_values, name="api_values"),
  path("api/v1/curves/filter", api.api_curves_filter, name="api_curves_filter"),
]
