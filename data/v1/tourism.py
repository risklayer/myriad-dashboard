from typing import List

from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Router
from ninja.decorators import decorate_view

from dashboard.settings import (
  API_CACHE_TIMEOUT,
)
from data.models import (
  TourismIndicator,
)
from data.schemas import (
  TourismIndicatorSchema,
)

router = Router(tags=["TOURISM"])


@router.get("/indicators", tags=["TOURISM"], response=List[TourismIndicatorSchema])
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def indicators(request: HttpRequest):
  """Returns a list of available Scenarios"""
  return [indicator.to_dict() for indicator in TourismIndicator.objects.all()]
