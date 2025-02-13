from typing import Dict, List
from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Query, Router
from ninja.decorators import decorate_view

from data.api_shared import (
  CACHE_TIMEOUT,
  CountriesEnum,
)
from data.models import DataTableColumn, DataTableColumnValue, Nuts2Area
from data.schemas import AreaValuesSchema

router = Router(tags=["Values"])


@router.get("", response=Dict[str, Dict[str, float]])
@decorate_view(cache_page(CACHE_TIMEOUT))
def values(
  request: HttpRequest,
  countries: list[CountriesEnum] = Query([]),
  columns: list[str] = Query([]),
  bbox: str = None,
):
  """Returns a tree of filtered values, grouped by column key and area key"""
  result = dict()

  data_columns = DataTableColumn.objects.all()

  if len(columns) > 0:
    data_columns = data_columns.filter(key__in=columns)

  nuts2area_filter = Nuts2Area.objects.all()

  if len(countries) > 0:
    nuts2area_filter = nuts2area_filter.filter(country__country_code__in=countries)

  if bbox and len(bbox):
    bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = bbox.split(",")
    nuts2area_filter = nuts2area_filter.filter(
      bbox_min_x__lt=bbox_max_x,
      bbox_min_y__lt=bbox_max_y,
      bbox_max_x__gt=bbox_min_x,
      bbox_max_y__gt=bbox_min_y,
    )

  for column in data_columns:
    result[column.key] = {}

  for value in DataTableColumnValue.objects.filter(
    data_table_column__in=data_columns, nuts_area__in=nuts2area_filter
  ):
    result[column.key][value.nuts_area.key] = value.value

  return result


@router.get("/area", response=AreaValuesSchema | Dict[str, float])
def area(request: HttpRequest, nuts2_key: str, columns: List[str] = Query([])):
  """Returns nuts2 area with all or selected values"""
  area = Nuts2Area.objects.get(key=nuts2_key)

  column_filter = (
    DataTableColumn.objects.filter(key__in=columns)
    if len(columns)
    else DataTableColumn.objects.all()
  )

  values = DataTableColumnValue.objects.filter(data_table_column__in=column_filter, nuts_area=area)

  return {
    "NUTS_ID": area.key,
    "country_id": area.country_id,
  } | {v.data_table_column.key: v.value for v in values}
