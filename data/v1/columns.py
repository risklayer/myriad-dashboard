from typing import List

from django.db.models import Q
from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Router
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
  TableMetaHazard,
  TableMetaReturnPeriod,
  TableMetaThreshold,
)
from data.schemas import (
  DataTableColumnSchema,
  DataTableColumnSummarySchema,
  TableMetaExposureSchema,
  TableMetaHazardSchema,
  TableMetaReturnPeriodSchema,
  TableMetaThresholdSchema,
)

router = Router(tags=["Columns"])


@router.get("", response=List[DataTableColumnSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def columns(
  request: HttpRequest,
  hazard: HazardOptionsEnum = "drought_drr",
  exposure: ExposureOptionsEnum = "agGDP",
  threshold: ThresholdOptionsEnum = "avg",
  return_period: ReturnPeriodOptionsEnum = None,
):
  """Returns a list of all data columns with their metadata"""
  columns = filter_columns(hazard, exposure, threshold, return_period)

  return columns


@router.get("/summaries", response=List[DataTableColumnSummarySchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def column_summaries(
  request: HttpRequest,
  hazard: HazardOptionsEnum = "drought_drr",
  exposure: ExposureOptionsEnum = "agGDP",
  threshold: ThresholdOptionsEnum = "avg",
  return_period: ReturnPeriodOptionsEnum = None,
):
  """Returns a list of all data columns keys, labels and descriptions"""
  columns = filter_columns(hazard, exposure, threshold, return_period)

  return columns


@router.get("/hazards", response=List[TableMetaHazardSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def hazards(request: HttpRequest):
  """Returns a list of all hazard types"""
  return TableMetaHazard.objects.all().order_by("label")


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


def filter_columns(hazard: str, exposure: str, threshold: str, return_period: str):
  hazard_filter = TableMetaHazard.objects.all()
  if hazard:
    hazard_filter = hazard_filter.filter(key=hazard)

  exposure_filter = TableMetaExposure.objects.all()
  if exposure:
    exposure_filter = exposure_filter.filter(key=exposure)

  threshold_filter = TableMetaThreshold.objects.all()
  if threshold:
    threshold_filter = threshold_filter.filter(key=threshold)

  return_period_filter = TableMetaReturnPeriod.objects.all()
  if return_period:
    return_period_filter = return_period_filter.filter(key=return_period)

  columns = (
    DataTableColumn.objects.filter(
      (Q(hazard__in=hazard_filter) | Q(hazard=None))
      & (Q(exposure__in=exposure_filter) | Q(exposure=None))
      & (Q(threshold__in=threshold_filter) | Q(threshold=None))
      & (Q(return_period__in=return_period_filter) | Q(return_period=None))
    )
    .select_related(
      "return_period",
      "hazard",
      "exposure",
      "threshold",
    )
    .order_by("key")
  )

  return columns
