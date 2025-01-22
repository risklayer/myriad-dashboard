from django.conf import settings
from django.shortcuts import render


def api_index(request):
  return render(request, "api/api_reference.html")


def api_openapi_yaml(request):
  return render(
    request, "api/openapi_v1.yaml", context={"hosts": settings.ALLOWED_HOSTS}
  )
