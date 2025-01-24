from django.db.models import Q

from .models import (
  Country,
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
  VulnerabilityCurve,
)


def api_curves_filter_json(parameters):
  hazard_options = CurveHazard.objects.all()
  if "hazard" in parameters and parameters["hazard"] != "":
    hazard_options = hazard_options.filter(key__in=parameters.getlist("hazard"))

  quality_options = CurveQuality.objects.all()
  if "quality" in parameters and parameters["quality"] != "":
    quality_options = quality_options.filter(key__in=parameters.getlist("quality"))

  con_description_1_options = CurveConstructionType1.objects.all()
  if "con_description_1" in parameters and parameters["con_description_1"] != "":
    con_description_1_options = con_description_1_options.filter(
      key__in=parameters.getlist("con_description_1")
    )

  con_description_2_options = CurveConstructionType2.objects.all()
  if "con_description_2" in parameters and parameters["con_description_2"] != "":
    con_description_2_options = con_description_2_options.filter(
      key__in=parameters.getlist("con_description_2")
    )

  con_description_3_options = CurveConstructionType3.objects.all()
  if "con_description_3" in parameters and parameters["con_description_3"] != "":
    con_description_3_options = con_description_3_options.filter(
      key__in=parameters.getlist("con_description_3")
    )

  occ_description_1_options = CurveOccupancyType1.objects.all()
  if "occ_description_1" in parameters and parameters["occ_description_1"] != "":
    occ_description_1_options = occ_description_1_options.filter(
      key__in=parameters.getlist("occ_description_1")
    )

  occ_description_2_options = CurveOccupancyType2.objects.all()
  if "occ_description_2" in parameters and parameters["occ_description_2"] != "":
    occ_description_2_options = occ_description_2_options.filter(
      key__in=parameters.getlist("occ_description_2")
    )

  occ_description_3_options = CurveOccupancyType3.objects.all()
  if "occ_description_3" in parameters and parameters["occ_description_3"] != "":
    occ_description_3_options = occ_description_3_options.filter(
      key__in=parameters.getlist("occ_description_3")
    )

  coverage_options = CurveCoverage.objects.all()
  if "coverage" in parameters and parameters["coverage"] != "":
    coverage_options = coverage_options.filter(key__in=parameters.getlist("coverage"))

  myriad_sectors_applicable_options = CurveSector.objects.all()
  if "myriad_sectors_applicable" in parameters and parameters["myriad_sectors_applicable"] != "":
    myriad_sectors_applicable_options = myriad_sectors_applicable_options.filter(
      key__in=parameters.getlist("myriad_sectors_applicable")
    )

  countries_options = Country.objects.all()
  if "countries" in parameters and parameters["countries"] != "":
    countries_options = countries_options.filter(country_code__in=parameters.getlist("countries"))

  curves = VulnerabilityCurve.objects.filter(
    (Q(hazard__in=hazard_options) | Q(hazard=None))
    & (Q(quality__in=quality_options) | Q(hazard=None))
    & (Q(con_description_1__in=con_description_1_options) | Q(hazard=None))
    & (Q(con_description_2__in=con_description_2_options) | Q(hazard=None))
    & (Q(con_description_3__in=con_description_3_options) | Q(hazard=None))
    & (Q(occ_description_1__in=occ_description_1_options) | Q(hazard=None))
    & (Q(occ_description_2__in=occ_description_2_options) | Q(hazard=None))
    & (Q(occ_description_3__in=occ_description_3_options) | Q(hazard=None))
    & (Q(coverage__in=coverage_options) | Q(hazard=None))
    & (Q(myriad_sectors_applicable__in=myriad_sectors_applicable_options) | Q(hazard=None))
    & (Q(countries__in=countries_options) | Q(hazard=None))
  )

  return {
    "new_filter_options": {
      "hazard_options": list(
        hazard_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "quality_options": list(
        quality_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "con_description_1_options": list(
        con_description_1_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "con_description_2_options": list(
        con_description_2_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "con_description_3_options": list(
        con_description_3_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "occ_description_1_options": list(
        occ_description_1_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "occ_description_2_options": list(
        occ_description_2_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "occ_description_3_options": list(
        occ_description_3_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "coverage_options": list(
        coverage_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "myriad_sectors_applicable_options": list(
        myriad_sectors_applicable_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("key", flat=True)
      ),
      "countries_options": list(
        countries_options.filter(vulnerabilitycurve__in=curves)
        .distinct()
        .values_list("country_code", flat=True)
      ),
    },
    "curves": [(c.key, c.label) for c in curves.distinct()],
  }
