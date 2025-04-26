from typing import Dict, List

from django.db.models import Q
from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Query, Router
from ninja.decorators import decorate_view

from data.api_shared import (
  CACHE_TIMEOUT,
  ExposureOptionsEnum,
  HazardOptionsEnum,
  ReturnPeriodOptionsEnum,
  ThresholdOptionsEnum,
)
from data.models import (
  DataTableColumn,
  TableMetaExposure,
  Hazard,
  TableMetaReturnPeriod,
  TableMetaThreshold,
  DataTableColumnMetadata,
  DataTableColumnMetadataValueFloat,
  DataTableColumnMetadataValueString,
)
from data.schemas import (
  DataTableColumnsWithFilterOptionsSchema,
  DataTableColumnSummaryWithFilterOptionsSchema,
  TableMetaExposureSchema,
  HazardSchema,
  TableMetaReturnPeriodSchema,
  TableMetaThresholdSchema,
  DataTableColumnSchema,
)

router = Router(tags=["Columns"])


@router.get("", response=DataTableColumnsWithFilterOptionsSchema)
@decorate_view(cache_page(CACHE_TIMEOUT))
def columns(
  request: HttpRequest,
  hazard: HazardOptionsEnum = None,
  exposure: ExposureOptionsEnum = None,
  threshold: ThresholdOptionsEnum = None,
  return_period: ReturnPeriodOptionsEnum = None,
  columns: List[str] = Query([]),
):
  """Returns a list of all data columns with their metadata"""
  columns, filter_options = filter_columns(
    hazard, exposure, threshold, return_period, columns, get_kwargs=request.GET
  )

  return {
    "columns": columns,
    "filter_options": filter_options,
  }


@router.get("/map", response=Dict[str, DataTableColumnSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def columns_map(
  request: HttpRequest,
  hazard: HazardOptionsEnum = None,
  exposure: ExposureOptionsEnum = None,
  threshold: ThresholdOptionsEnum = None,
  return_period: ReturnPeriodOptionsEnum = None,
  columns: List[str] = Query([]),
):
  """Returns a list of all data columns with their metadata"""
  columns, _ = filter_columns(
    hazard, exposure, threshold, return_period, columns, get_kwargs=request.GET
  )

  return {c.key: c for c in columns}


@router.get("/summaries", response=DataTableColumnSummaryWithFilterOptionsSchema)
@decorate_view(cache_page(CACHE_TIMEOUT))
def column_summaries(
  request: HttpRequest,
  hazard: HazardOptionsEnum = None,
  exposure: ExposureOptionsEnum = None,
  threshold: ThresholdOptionsEnum = None,
  return_period: ReturnPeriodOptionsEnum = None,
  columns: List[str] = Query([]),
):
  """Returns a list of all data columns keys, labels and descriptions"""
  columns, filter_options = filter_columns(
    hazard, exposure, threshold, return_period, columns, get_kwargs=request.GET
  )

  return {
    "columns": columns,
    "filter_options": filter_options,
  }


@router.get("/hazards", response=List[HazardSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def hazards(request: HttpRequest):
  """Returns a list of all hazard types"""
  return Hazard.objects.all().order_by("label")


@router.get("/exposure_types", response=List[TableMetaExposureSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def exposure_types(request: HttpRequest):
  """Returns a list of all exposure types"""
  return TableMetaExposure.objects.all().order_by("label")


@router.get("/thresholds", response=List[TableMetaThresholdSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def thresholds(request: HttpRequest):
  """Returns a list of all thresholds types"""
  return TableMetaThreshold.objects.all().order_by("label")


@router.get("/return_periods", response=List[TableMetaReturnPeriodSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def return_periods(request: HttpRequest):
  """Returns a list of all return periods"""
  return TableMetaReturnPeriod.objects.all().order_by("label")


def filter_columns(
  hazard: str,
  exposure: str,
  threshold: str,
  return_period: str,
  column_keys: List[str],
  get_kwargs,
):
  filtered_columns = DataTableColumn.objects.all()

  hazard_filter = None
  exposure_filter = None
  threshold_filter = None
  return_period_filter = None
  column_keys_filter = None

  if hazard:
    hazard_filter = Hazard.objects.objects.filter(key=hazard)
    filtered_columns = filtered_columns.filter(Q(hazard__in=hazard_filter) | Q(hazard=None))

  if exposure:
    exposure_filter = TableMetaExposure.objects.filter(key=exposure)
    filtered_columns = filtered_columns.filter(Q(exposure__in=exposure_filter) | Q(exposure=None))

  if threshold:
    threshold_filter = TableMetaThreshold.objects.filter(key=threshold)
    filtered_columns = filtered_columns.filter(
      Q(threshold__in=threshold_filter) | Q(threshold=None)
    )

  if return_period:
    return_period_filter = TableMetaReturnPeriod.objects.filter(key=return_period)
    filtered_columns = filtered_columns.filter(
      Q(return_period__in=return_period_filter) | Q(return_period=None)
    )

  if len(column_keys):
    column_keys_filter = set(column_keys)
    filtered_columns = filtered_columns.filter(Q(key__in=column_keys_filter) | Q(key=None))

  for key in get_kwargs.keys():
    if not key.startswith("metadata_"):
      continue

    metadata_key = key.replace("metadata_", "")

    if metadata_key.endswith("__max"):
      metadata_key = metadata_key.replace("__max", "")
      # we assume only one parameter is set here

      metadata = DataTableColumnMetadata.objects.get(key=metadata_key)

      if metadata.type == "float":
        metadata_values = DataTableColumnMetadataValueFloat.objects.filter(
          metadata=metadata, value__lte=get_kwargs[key]
        )
        filtered_columns = filtered_columns.filter(
          datatablecolumnmetadatavaluefloat__in=metadata_values
        )

    elif metadata_key.endswith("__min"):
      metadata_key = metadata_key.replace("__min", "")
      # we assume only one parameter is set here

      metadata = DataTableColumnMetadata.objects.get(key=metadata_key)

      if metadata.type == "float":
        metadata_values = DataTableColumnMetadataValueFloat.objects.filter(
          metadata=metadata, value__gte=get_kwargs[key]
        )
        filtered_columns = filtered_columns.filter(
          datatablecolumnmetadatavaluefloat__in=metadata_values
        )
    else:
      metadata = DataTableColumnMetadata.objects.get(key=metadata_key)

      meta_or = Q(id__in=[])
      for value in get_kwargs.getlist(key):
        if metadata.type == "float":
          metadata_values = DataTableColumnMetadataValueFloat.objects.filter(
            metadata=metadata, value=value
          )
          meta_or |= Q(datatablecolumnmetadatavaluefloat__in=metadata_values)
        elif metadata.type == "string":
          metadata_values = DataTableColumnMetadataValueString.objects.filter(
            metadata=metadata, value=value
          )
          meta_or |= Q(datatablecolumnmetadatavaluestring__in=metadata_values)
        else:
          raise Exception("unknown metadata type: " + metadata.type)

      filtered_columns = filtered_columns.filter(meta_or)

  # TODO: if empty, return None, empty list or remove from object?
  filter_options = {
    "hazard_options": hazard_filter,
    "exposure_options": exposure_filter,
    "threshold_options": threshold_filter,
    "return_period_options": return_period_filter,
  }

  for key in filter_options.keys():
    if filter_options[key] is not None:
      filter_options[key] = (
        filter_options[key]
        .filter(datatablecolumn__in=filtered_columns)
        .distinct()
        .values_list("key", flat="True")
      )

  for metadata in DataTableColumnMetadata.objects.filter(
    Q(datatablecolumnmetadatavaluefloat__column__in=filtered_columns)
    | Q(datatablecolumnmetadatavaluestring__column__in=filtered_columns)
  ):
    if metadata.type == "float":
      filter_options[metadata.key] = (
        DataTableColumnMetadataValueString.objects.filter(column__in=filtered_columns)
        .distinct()
        .values_list("value", flat="True")
      )
    elif metadata.type == "string":
      filter_options[metadata.key] = (
        DataTableColumnMetadataValueFloat.objects.filter(column__in=filtered_columns)
        .distinct()
        .values_list("value", flat="True")
      )
    else:
      raise Exception("unknown metadata type")

  columns = filtered_columns.select_related(
    "return_period",
    "hazard",
    "exposure",
    "threshold",
  ).order_by("key")

  return columns, filter_options
