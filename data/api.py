from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_http_methods

from django.db.models import Q

from .curves import api_curves_filter_json

from .models import (
  Country,
  DataTableColumn,
  DataTableColumnValue,
  Nuts2Area,
  TableMetaHazard,
  TableMetaExposure,
  TableMetaThreshold,
  TableMetaReturnPeriod,
)


@require_http_methods(["GET"])
def api_countries(request: HttpRequest):
  country_list = [c.to_dict() for c in Country.objects.all()]
  return JsonResponse(
    {
      "country_list": country_list,
      "country_map": {c["country_code"]: c for c in country_list},
    }
  )


@require_http_methods(["GET"])
def api_nuts2areas(request: HttpRequest):
  nuts2area_filter = Nuts2Area.objects.all()
  if "bbox" in request.GET:
    bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = request.GET["bbox"].split(",")
    nuts2area_filter = nuts2area_filter.filter(
      bbox_min_x__lt=bbox_max_x,
      bbox_min_y__lt=bbox_max_y,
      bbox_max_x__gt=bbox_min_x,
      bbox_max_y__gt=bbox_min_y,
    )

  countries = request.GET.getlist("country", [])
  if len(countries) > 0:
    nuts2area_filter = nuts2area_filter.filter(country__country_code__in=countries)

  nuts2areas_list = [c.to_dict() for c in nuts2area_filter]

  return JsonResponse(
    {
      "nuts2areas_list": nuts2areas_list,
      "nuts2areas_map": {c["key"]: c for c in nuts2areas_list},
    }
  )


@require_http_methods(["GET"])
def api_nuts2shapes(request: HttpRequest):
  nuts2area_filter = Nuts2Area.objects.all()

  if "bbox" in request.GET:
    bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = request.GET["bbox"].split(",")

    nuts2area_filter = nuts2area_filter.filter(
      bbox_min_x__lt=bbox_max_x,
      bbox_min_y__lt=bbox_max_y,
      bbox_max_x__gt=bbox_min_x,
      bbox_max_y__gt=bbox_min_y,
    )

  countries = request.GET.getlist("country", [])
  if len(countries) > 0:
    nuts2area_filter = nuts2area_filter.filter(country__country_code__in=countries)

  return JsonResponse(
    {
      "type": "FeatureCollection",
      "name": "nuts3",
      "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
      "features": [
        {
          "type": "Feature",
          "properties": {
            "NUTS_ID": area.key,
            "country_id": area.country_id,
          },
          "geometry": area.geom_json,
        }
        for area in nuts2area_filter
      ],
    }
  )


@require_http_methods(["GET"])
def api_column_hazard(request: HttpRequest):
  hazard_list = [c.to_dict() for c in TableMetaHazard.objects.all()]
  return JsonResponse(
    {
      "hazard_list": hazard_list,
      "hazard_map": {c["key"]: c for c in hazard_list},
    }
  )


@require_http_methods(["GET"])
def api_column_exposure(request: HttpRequest):
  exposure_list = [c.to_dict() for c in TableMetaExposure.objects.all()]
  return JsonResponse(
    {
      "exposure_list": exposure_list,
      "exposure_map": {c["key"]: c for c in exposure_list},
    }
  )


@require_http_methods(["GET"])
def api_column_threshold(request: HttpRequest):
  threshold_list = [c.to_dict() for c in TableMetaThreshold.objects.all()]
  return JsonResponse(
    {
      "threshold_list": threshold_list,
      "threshold_map": {c["key"]: c for c in threshold_list},
    }
  )


@require_http_methods(["GET"])
def api_column_return_period(request: HttpRequest):
  return_period_list = [c.to_dict() for c in TableMetaReturnPeriod.objects.all()]
  return JsonResponse(
    {
      "return_period_list": return_period_list,
      "return_period_map": {c["key"]: c for c in return_period_list},
    }
  )


@require_http_methods(["GET"])
def api_columns(request: HttpRequest):
  hazard_filter = TableMetaHazard.objects.all()
  if "hazard" in request.GET:
    hazard_filter = hazard_filter.filter(key=request.GET["hazard"])

  exposure_filter = TableMetaExposure.objects.all()
  if "exposure" in request.GET:
    exposure_filter = exposure_filter.filter(key=request.GET["exposure"])

  threshold_filter = TableMetaThreshold.objects.all()
  if "threshold" in request.GET:
    threshold_filter = threshold_filter.filter(key=request.GET["threshold"])

  return_period_filter = TableMetaReturnPeriod.objects.all()
  if "return_period" in request.GET:
    return_period_filter = return_period_filter.filter(key=request.GET["return_period"])

  columns = DataTableColumn.objects.filter(
    (Q(hazard__in=hazard_filter) | Q(hazard=None))
    & (Q(exposure__in=exposure_filter) | Q(exposure=None))
    & (Q(threshold__in=threshold_filter) | Q(threshold=None))
    & (Q(return_period__in=return_period_filter) | Q(return_period=None))
  )

  column_list = [c.to_dict(flat=False) for c in columns]

  return JsonResponse(
    {
      "column_list": column_list,
      "column_map": {c["key"]: c for c in column_list},
    }
  )


@require_http_methods(["GET"])
def api_values(request: HttpRequest):
  result = dict()

  columns = DataTableColumn.objects.all()
  if "columns" in request.GET:
    columns = columns.filter(key__in=request.GET["columns"].split(","))

  nuts2area_filter = Nuts2Area.objects.all()

  countries = request.GET.getlist("country", [])
  if len(countries) > 0:
    nuts2area_filter = nuts2area_filter.filter(country__country_code__in=countries)

  if "bbox" in request.GET:
    bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = request.GET["bbox"].split(",")
    nuts2area_filter = nuts2area_filter.filter(
      bbox_min_x__lt=bbox_max_x,
      bbox_min_y__lt=bbox_max_y,
      bbox_max_x__gt=bbox_min_x,
      bbox_max_y__gt=bbox_min_y,
    )

  for column in columns:
    column_data = dict()

    for value in DataTableColumnValue.objects.filter(
      data_table_column=column, nuts_area__in=nuts2area_filter
    ):
      column_data[value.nuts_area.key] = value.value

    result[column.key] = column_data

  return JsonResponse(result)


@require_http_methods(["GET"])
def api_curves_filter(request: HttpRequest):
  return JsonResponse(api_curves_filter_json(request.GET))
