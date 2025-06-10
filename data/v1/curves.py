from typing import List
from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Query, Router
from ninja.decorators import decorate_view

from dashboard.settings import (
  API_CACHE_TIMEOUT,
)
from data.api_shared import CountriesEnum, HazardOptionsEnum
from data.curves import curves_filter_json

router = Router(tags=["Curves"])


@router.get("/curves_filter", tags=["Curves"])
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def curves_filter(
  request: HttpRequest,
  hazard: Query[HazardOptionsEnum],
  countries: Query[CountriesEnum] = None,  # type: ignore
  quality: Query[str] = None,  # type: ignore
  con_description_1: Query[str] = None,  # type: ignore
  con_description_2: Query[str] = None,  # type: ignore
  con_description_3: Query[str] = None,  # type: ignore
  occ_description_1: Query[str] = None,  # type: ignore
  occ_description_2: Query[str] = None,  # type: ignore
  occ_description_3: Query[str] = None,  # type: ignore
  coverage: Query[str] = None,  # type: ignore
  myriad_sectors_applicable: Query[str] = None,  # type: ignore
):
  """Returns curve filter options based on what curves are available with the provided filters"""
  return curves_filter_json(request.GET)
