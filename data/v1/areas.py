from typing import Dict, List

from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from geojson_pydantic import FeatureCollection
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
  Nuts2Area,
)
from data.schemas import (
  CountrySchema,
  Nuts2AreaSchema,
  ShapeFeature,
)

router = Router(tags=["Areas"])


@router.get("", response=List[Nuts2AreaSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def areas(request: HttpRequest, bbox: str = "", countries: List[CountriesEnum] = Query([])):
  """Returns an array of selected NUTS2 areas"""
  nuts2areas = filter_nuts2_areas(bbox, countries)
  return nuts2areas


@router.get("/map", response=Dict[str, Nuts2AreaSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def shapes_map(
  request: HttpRequest,
  bbox: str = "",
  countries: List[CountriesEnum] = Query([]),
):
  """Returns a map of selected NUTS2 areas"""
  nuts2areas = filter_nuts2_areas(bbox, countries)

  return {c.key: c for c in nuts2areas}


@router.get("/shapes", response=FeatureCollection[ShapeFeature])
@decorate_view(cache_page(CACHE_TIMEOUT))
def shapes(
  request: HttpRequest,
  bbox: str = "",
  countries: List[CountriesEnum] = Query([]),
  columns: List[str] = Query([]),
):
  """Returns a list of all NUTS2 shapes in a GeoJSON FeatureCollection, including column values if specified"""
  nuts2area_filter = Nuts2Area.objects.all()

  if bbox:
    bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = bbox

    nuts2area_filter = nuts2area_filter.filter(
      bbox_min_x__lt=bbox_max_x,
      bbox_min_y__lt=bbox_max_y,
      bbox_max_x__gt=bbox_min_x,
      bbox_max_y__gt=bbox_min_y,
    )

  if len(countries) > 0:
    nuts2area_filter = nuts2area_filter.filter(country__country_code__in=countries)

  column_filter = list(DataTableColumn.objects.filter(key__in=columns)) if len(columns) else []

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
        | {
          c.key: DataTableColumnValue.objects.get(data_table_column=c, nuts_area=area).value
          for c in column_filter
        },
        "geometry": area.geom_json,
      }
      for area in nuts2area_filter
    ],
  }


@router.get("/countries", response=List[CountrySchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def countries(request: HttpRequest):
  """Returns a list of all countries"""
  return Country.objects.all().order_by("label")


def filter_nuts2_areas(bbox: str, countries: List[CountriesEnum]):
  nuts2areas = Nuts2Area.objects.all()
  if bbox:
    bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = bbox
    nuts2areas = nuts2areas.filter(
      bbox_min_x__lt=bbox_max_x,
      bbox_min_y__lt=bbox_max_y,
      bbox_max_x__gt=bbox_min_x,
      bbox_max_y__gt=bbox_min_y,
    )

  if len(countries) > 0:
    nuts2areas = nuts2areas.filter(country__country_code__in=countries)
  return nuts2areas
