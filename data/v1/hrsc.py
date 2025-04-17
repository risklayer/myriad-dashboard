from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Router
from ninja.decorators import decorate_view
from django.db.models import Q

from typing import List

from django.conf import settings

from data.api_shared import (
  CACHE_TIMEOUT,
)
from data.models import (
  HrscScenario,
  HrscEventCollection,
  HrscEvent,
  HrscValueCoordinateWinterstorm,
  HrscEventMetadata,
  HrscEventMetadataValueFloat,
  HrscEventMetadataValueString,
  HrscHazardProbabilityRaster,
  HrscExposure,
)

from django.contrib.gis.measure import Distance as MDistance
from django.contrib.gis.geos import Point

from django.contrib.gis.db.models.functions import Distance as DBDistance


from data.schemas import (
  HrscScenarioSchema,
  HrscEventSchema,
  HrscEventCollectionSchema,
  HrscHazardProbabilityRasterSchema,
  HrscExposureSchema,
)


router = Router(tags=["HRSC"])


@router.get("/scenarios", tags=["HRSC"], response=List[HrscScenarioSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def scenarios(request: HttpRequest):
  """Returns a list of available Scenarios"""
  return [scenario.to_dict() for scenario in HrscScenario.objects.all()]


@router.get("/exposures", tags=["HRSC"], response=List[HrscExposureSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def exposures(request: HttpRequest):
  """Returns a list of available Exposures"""
  return [exposure.to_dict() for exposure in HrscExposure.objects.all()]


@router.get("/collections", tags=["HRSC"], response=List[HrscEventCollectionSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def collections(request: HttpRequest):
  """Returns a list of available Collections"""
  return [collection.to_dict() for collection in HrscEventCollection.objects.all()]


@router.get("/event/{str:id}/detail", tags=["HRSC"], response=HrscEventSchema)
@decorate_view(cache_page(CACHE_TIMEOUT))
def event_by_id(request: HttpRequest, id: int, bbox: str = ""):
  """Returns the event details including footprint"""
  return HrscEvent.objects.get(id=id).to_dict(
    include_footprint_blob=True, footprint_bbox=bbox.split(",")
  )


# removed this endpoint, not efficient enough
# @router.get("/events/{str:collection_key}", tags=["HRSC"], response=List[HrscEventSchema])
# @decorate_view(cache_page(CACHE_TIMEOUT))
# def events_by_collection(request: HttpRequest, collection_key: str):
#  """Returns a list of events inside this collection"""
#  return [event.to_dict() for event in HrscEventCollection.objects.get(key=collection_key).hrscevent_set.all()]


@router.get("/events/winterstorm/filter", tags=["HRSC"], response=List[HrscEventSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def events_by_collection_filter_ws(
  request: HttpRequest,
  longitude: float = None,
  latitude: float = None,
  radius: float = 1000,
  value_min: float = None,
  value_max: float = None,
  limit: int = 100,
):
  """
  Filter Winterstorm events by location, radius and parameters.
  Due to witnerstorms covering a large and diffuse area, we filter
  by wind speed inside the footprints
  """

  point = Point(longitude, latitude, srid=settings.DEFAULT_SRID)

  values = HrscValueCoordinateWinterstorm.objects.filter(
    event__collection=HrscEventCollection.objects.get(key="winterstorm"),
    location__location__distance_lt=(point, MDistance(km=radius)),
  )

  if value_min:
    values = values.filter(value__gte=value_min)

  if value_max:
    values = values.filter(value__lte=value_max)

  values = values.annotate(
    distance=DBDistance("location__location", point, geography=True)
  ).order_by("distance")

  events = HrscEvent.objects.filter(id__in=values.values("event").distinct()[:limit])

  return [event.to_dict() for event in events]


@router.get("/events/{str:collection_key}/filter", tags=["HRSC"], response=List[HrscEventSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def events_by_collection_filter(
  request: HttpRequest,
  collection_key: str,
  longitude: float = None,
  latitude: float = None,
  radius: float = 1000,
  limit: int = 100,
):
  """Filter events by location, radius and parameters"
  We support passing of arbitrary metadata fields:

  * "metadata_&lt;key&gt;": <key> is the metadata key that has to be equal,
    a list can also be supplied which will be or'ed

  * "metadata_&lt;key&gt;__max" or "__min": upper or lower boundary
    (note: 2 underscores)
  """

  events = HrscEvent.getByLocation(
    point=None,
    longitude=longitude,
    latitude=latitude,
    radius=radius,
    limit=None,
    event_filter=HrscEventCollection.objects.get(key=collection_key).hrscevent_set.all(),
  )

  for key in request.GET.keys():
    if not key.startswith("metadata_"):
      continue

    metadata_key = key.replace("metadata_", "")

    if metadata_key.endswith("__max"):
      metadata_key = metadata_key.replace("__max", "")
      # we assume only one parameter is set here

      metadata = HrscEventMetadata.objects.get(key=metadata_key)

      if metadata.type == "float":
        metadata_values = HrscEventMetadataValueFloat.objects.filter(
          metadata=metadata, value__lte=request.GET[key]
        )
        events = events.filter(hrsceventmetadatavaluefloat__in=metadata_values)

    elif metadata_key.endswith("__min"):
      metadata_key = metadata_key.replace("__min", "")
      # we assume only one parameter is set here

      metadata = HrscEventMetadata.objects.get(key=metadata_key)

      if metadata.type == "float":
        metadata_values = HrscEventMetadataValueFloat.objects.filter(
          metadata=metadata, value__gte=request.GET[key]
        )
        events = events.filter(hrsceventmetadatavaluefloat__in=metadata_values)
    else:
      metadata = HrscEventMetadata.objects.get(key=metadata_key)

      meta_or = Q(id__in=[])
      for value in request.GET.getlist(key):
        if metadata.type == "float":
          metadata_values = HrscEventMetadataValueFloat.objects.filter(
            metadata=metadata, value=value
          )
          meta_or |= Q(hrsceventmetadatavaluefloat__in=metadata_values)
        elif metadata.type == "string":
          metadata_values = HrscEventMetadataValueString.objects.filter(
            metadata=metadata, value=value
          )
          meta_or |= Q(hrsceventmetadatavaluestring__in=metadata_values)
        else:
          raise Exception("unknown metadata type: " + metadata.type)

      events = events.filter(meta_or)

  events = events[:limit]

  return [event.to_dict() for event in events]


@router.get(
  "/hazard_probabilities/raster/list",
  tags=["HRSC"],
  response=List[HrscHazardProbabilityRasterSchema],
)
@decorate_view(cache_page(CACHE_TIMEOUT))
def hazard_probabilities_raster_list(request: HttpRequest):
  """Return a probability value for a given hazard and severity"""
  return [r.to_dict() for r in HrscHazardProbabilityRaster.objects.all()]


@router.get("/hazard_probabilities/raster/value/{str:hazard_key}", tags=["HRSC"], response=float)
@decorate_view(cache_page(CACHE_TIMEOUT))
def hazard_probabilities_raster_value(
  request: HttpRequest,
  hazard_key: str,
  longitude: float,
  latitude: float,
  severity: float,
):
  """Return a probability value for a given hazard and severity"""
  return HrscHazardProbabilityRaster.objects.get(hazard__key=hazard_key).get_probability_value(
    severity, longitude, latitude
  )
