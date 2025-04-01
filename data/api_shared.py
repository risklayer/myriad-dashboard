from enum import StrEnum

from data.models import (
  Country,
  TableMetaExposure,
  Hazard,
  TableMetaReturnPeriod,
  TableMetaThreshold,
)


CACHE_TIMEOUT = 1000

# Dynamic "Enum" types for the purpose of displaying options in swagger
# Need to determine if this will create issues after importing data,
# e.g. might require a server restart before using API.
# They are specified as StrEnum so they don't need to be coercer to strings for
# use in queries (since the models don't use enums)
countries = dict()
hazards = dict()
table_meta_exposures = dict()
table_meta_thresholds = dict()
table_meta_return_periods = dict()

try:
  countries = dict(
    map(lambda c: (c.label, c.country_code), Country.objects.all().order_by("country_code"))
  )
  hazards = dict(map(lambda c: (c.key, c.key), Hazard.objects.all().order_by("key")))
  table_meta_exposures = dict(
    map(lambda c: (c.key, c.key), TableMetaExposure.objects.all().order_by("key"))
  )
  table_meta_thresholds = dict(
    map(lambda c: (c.key, c.key), TableMetaThreshold.objects.all().order_by("key"))
  )
  table_meta_return_periods = dict(
    map(lambda c: (c.key, c.key), TableMetaReturnPeriod.objects.all().order_by("key"))
  )
except Exception:
  pass

CountriesEnum = StrEnum(
  "CountriesEnum",
  {"All": "ALL"} | countries,
)

HazardOptionsEnum = StrEnum(
  "HazardOptionsEnum",
  hazards,
)

ExposureOptionsEnum = StrEnum(
  "ExposureOptionsEnum",
  table_meta_exposures,
)

ThresholdOptionsEnum = StrEnum(
  "ThresholdOptionsEnum",
  table_meta_thresholds,
)

ReturnPeriodOptionsEnum = StrEnum(
  "ReturnPeriodOptionsEnum",
  table_meta_return_periods,
)
