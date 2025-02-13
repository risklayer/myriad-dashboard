from enum import StrEnum

from data.models import (
  Country,
  TableMetaExposure,
  TableMetaHazard,
  TableMetaReturnPeriod,
  TableMetaThreshold,
)


CACHE_TIMEOUT = 1

# Dynamic "Enum" types for the purpose of displaying options in swagger
# Need to determine if this will create issues after importing data,
# e.g. might require a server restart before using API.
# They are specified as StrEnum so they don't need to be coercer to strings for
# use in queries (since the models don't use enums)
countries = []
table_meta_hazards = []
table_meta_exposures = []
table_meta_thresholds = []
table_meta_return_periods = []

try:
  countries = dict(
    map(lambda c: (c.label, c.country_code), Country.objects.all().order_by("country_code"))
  )
  table_meta_hazards = dict(
    map(lambda c: (c.key, c.key), TableMetaHazard.objects.all().order_by("key"))
  )
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
  countries,
)

HazardOptionsEnum = StrEnum(
  "HazardOptionsEnum",
  table_meta_hazards,
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
