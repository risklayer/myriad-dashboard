from typing import Dict, List

from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Query, Router
from ninja.decorators import decorate_view

from data.api_shared import (
  CACHE_TIMEOUT,
  CountriesEnum,
)
from data.models import (
  Country,
  DataTableColumn,
  DataTableColumnValue,
  Nuts3Area,
  TourismIndicator,
  TourismIndicatorValueString,
  TourismIndicatorValueFloat,
)
from data.schemas import (
  CountrySchema,
  FeatureCollectionSchema,
  Nuts3AreaSchema,
)

router = Router(tags=["Areas"])


@router.get("", response=List[Nuts3AreaSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def areas(request: HttpRequest, bbox: str = "", countries: List[CountriesEnum] = Query([])):
  """Returns an array of selected NUTS2 areas"""
  nuts3areas = filter_nuts3_areas(bbox, countries)
  return nuts3areas


@router.get("/map", response=Dict[str, Nuts3AreaSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def map(
  request: HttpRequest,
  bbox: str = "",
  countries: List[CountriesEnum] = Query([]),
):
  """Returns a map of selected NUTS2 areas"""
  nuts3areas = filter_nuts3_areas(bbox, countries)

  return {c.key: c for c in nuts3areas}


@router.get("/shapes", response=FeatureCollectionSchema)
@decorate_view(cache_page(CACHE_TIMEOUT))
def shapes(
  request: HttpRequest,
  bbox: str = "",
  countries: List[CountriesEnum] = Query([]),
  columns: List[str] = Query([]),
  nuts3areas: List[str] = Query([]),
  tourismIndicators: List[str] = Query([]),
):
  """Returns a list of all NUTS2 shapes in a GeoJSON FeatureCollection, including column values if specified.
  If using bbox, countries and nuts3areas will be ignored. If not using bbox, all nuts3areas are returned filtered by
  either country or nuts3areas, or both. Please note that nuts3areas and countries as filter are working together additively.
  """
  nuts3area_filter = Nuts3Area.objects.all()

  if bbox:
    bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = bbox.split(",")

    nuts3area_filter = Nuts3Area.objects.filter(
      bbox_min_x__lt=bbox_max_x,
      bbox_min_y__lt=bbox_max_y,
      bbox_max_x__gt=bbox_min_x,
      bbox_max_y__gt=bbox_min_y,
    )
  elif (len(countries) > 0 or len(nuts3areas) > 0) and "ALL" not in countries:
    nuts3area_filter = Nuts3Area.objects.none()
    if len(countries) > 0:
      nuts3area_filter |= Nuts3Area.objects.filter(country__country_code__in=countries)

    if len(nuts3areas) > 0:
      nuts3area_filter |= Nuts3Area.objects.filter(key__in=nuts3areas)

  value_dict = {
    key : dict() for key in nuts3area_filter.values_list("key", flat=True)
  }

  for column in DataTableColumn.objects.filter(key__in=columns):
    all_values = DataTableColumnValue.objects.filter(
      data_table_column=column, nuts_area__in=nuts3area_filter
    ).select_related("nuts_area")

    for value in all_values:
      value_dict[value.nuts_area_id][value.data_table_column.key] = value.value

  for indicator in TourismIndicator.objects.filter(key__in=tourismIndicators):
    all_values = TourismIndicatorValueString.objects.filter(
      indicator=indicator, nuts_area__in=nuts3area_filter
    ).select_related("nuts_area")

    for value in all_values:
      value_dict[value.nuts_area_id][value.data_table_column.key] = value.value

    all_values = TourismIndicatorValueFloat.objects.filter(
      indicator=indicator, nuts_area__in=nuts3area_filter
    ).select_related("nuts_area")

    for value in all_values:
      value_dict[value.nuts_area_id][value.data_table_column.key] = value.value

  return {
    "type": "FeatureCollection",
    "name": "nuts3",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": [
      {
        "type": "Feature",
        "properties": {
          "NUTS_ID": area.key,
          "country_id": area.country.country_code,
        }
        | value_dict.get(area.id, dict()),
        "geometry": area.geom_json,
      }
      for area in nuts3area_filter
    ],
  }


@router.get("/countries", response=List[CountrySchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def countries(request: HttpRequest):
  """Returns a list of all countries"""
  return Country.objects.all().order_by("label")


def filter_nuts3_areas(bbox: str, countries: List[CountriesEnum]):
  nuts3areas = Nuts3Area.objects.all()
  if bbox:
    bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = bbox
    nuts3areas = nuts3areas.filter(
      bbox_min_x__lt=bbox_max_x,
      bbox_min_y__lt=bbox_max_y,
      bbox_max_x__gt=bbox_min_x,
      bbox_max_y__gt=bbox_min_y,
    )

  if len(countries) > 0 and "ALL" not in countries:
    nuts3areas = nuts3areas.filter(country__country_code__in=countries)
  return nuts3areas
