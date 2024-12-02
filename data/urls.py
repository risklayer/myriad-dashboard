from django.urls import path

from . import api_static

urlpatterns = [
  path('api/v1/', api_static.api_index, name='index'),
  path('api/v1/openapi.yaml', api_static.api_openapi_yaml, name='openapi_yaml'),

]
