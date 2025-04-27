from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Router
from ninja.decorators import decorate_view

from dashboard.settings import (
  API_CACHE_TIMEOUT,
)
from data.curves import curves_filter_json

router = Router(tags=["Curves"])


@router.get("/curves_filter", tags=["Curves"])
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def curves_filter(request: HttpRequest):
  """Returns curve filter options based on what curves are available with the provided filters"""
  return curves_filter_json(request.GET)
