from data.models import (
  CurveConstructionType1,
  CurveConstructionType2,
  CurveConstructionType3,
  CurveCoverage,
  CurveHazard,
  CurveOccupancyType1,
  CurveOccupancyType2,
  CurveOccupancyType3,
  CurveQuality,
  CurveSector,
  Country,
  TableMetaExposure,
  TableMetaHazard,
  TableMetaThreshold,
  TableMetaReturnPeriod,
)
from django.conf import settings
from django.shortcuts import render


def api_index(request):
  return render(request, "api/api_reference.html")


def api_openapi_yaml(request):
  return render(
    request,
    "api/openapi_v1.yaml",
    context={
      "hosts": settings.ALLOWED_HOSTS,
      "col_hazard_options": TableMetaHazard.objects.all().values_list("key", flat=True),
      "col_exposure_filter_options": TableMetaExposure.objects.all().values_list("key", flat=True),
      "col_threshold_filter_options": TableMetaThreshold.objects.all().values_list(
        "key", flat=True
      ),
      "col_return_period_filter_options": TableMetaReturnPeriod.objects.all().values_list(
        "key", flat=True
      ),
      "hazard_options": CurveHazard.objects.all().values_list("key", flat=True),
      "quality_options": CurveQuality.objects.all().values_list("key", flat=True),
      "con_description_1_options": CurveConstructionType1.objects.all().values_list(
        "key", flat=True
      ),
      "con_description_2_options": CurveConstructionType2.objects.all().values_list(
        "key", flat=True
      ),
      "con_description_3_options": CurveConstructionType3.objects.all().values_list(
        "key", flat=True
      ),
      "occ_description_1_options": CurveOccupancyType1.objects.all().values_list("key", flat=True),
      "occ_description_2_options": CurveOccupancyType2.objects.all().values_list("key", flat=True),
      "occ_description_3_options": CurveOccupancyType3.objects.all().values_list("key", flat=True),
      "coverage_options": CurveCoverage.objects.all().values_list("key", flat=True),
      "myriad_sectors_applicable_options": CurveSector.objects.all().values_list("key", flat=True),
      "countries_options": Country.objects.all().values_list("country_code", flat=True),
    },
  )
