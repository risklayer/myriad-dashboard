from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Country, DataTableColumn, DataTableColumnValue, Nuts2Area


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
      bbox_min_x__gt=bbox_min_x,
      bbox_min_y__gt=bbox_min_y,
      bbox_max_x__lt=bbox_max_x,
      bbox_max_y__lt=bbox_max_y,
    )

  nuts2areas_list = [c.to_dict() for c in nuts2area_filter]

  return JsonResponse(
    {
      "nuts2areas_list": nuts2areas_list,
      "nuts2areas_map": {c["key"]: c for c in nuts2areas_list},
    }
  )


@require_http_methods(["GET"])
def api_columns(request: HttpRequest):
  column_list = [c.to_dict() for c in DataTableColumn.objects.all()]

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

  for column in columns:
    column_data = dict()

    nuts2area_filter = Nuts2Area.objects.all()
    if "bbox" in request.GET:
      bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = request.GET["bbox"].split(",")
      nuts2area_filter = nuts2area_filter.filter(
        bbox_min_x__gt=bbox_min_x,
        bbox_min_y__gt=bbox_min_y,
        bbox_max_x__lt=bbox_max_x,
        bbox_max_y__lt=bbox_max_y,
      )

    for value in DataTableColumnValue.objects.filter(
      data_table_column=column, nuts_area__in=nuts2area_filter
    ):
      column_data[value.nuts_area.key] = value.value

    result[column.key] = column_data

  return JsonResponse(result)
