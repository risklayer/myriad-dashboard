from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Router
from ninja.decorators import decorate_view

from typing import List

from django.conf import settings

from data.api_shared import (
  CACHE_TIMEOUT,
)
from data.models import (
  HrscScenarioType,
  HrscEventCollection,
  HrscEvent,
  HrscValueCoordinateWinterstorm,
  HrscEventMetadata,
  HrscEventMetadataValueFloat,
  HrscEventMetadataValueString,
)

from django.contrib.gis.measure import Distance as MDistance
from django.contrib.gis.geos import Point

from django.contrib.gis.db.models.functions import Distance as DBDistance


from data.schemas import (
  HrscScenarioTypeScheme,
  HrscEventScheme,
)


router = Router(tags=["HRSC"])


@router.get("/scenarios", tags=["HRSC"], response=List[HrscScenarioTypeScheme])
@decorate_view(cache_page(CACHE_TIMEOUT))
def scenarios(request: HttpRequest):
  """Returns a list of available Scenarios"""
  return [scenario.to_dict() for scenario in HrscScenarioType.objects.all()]


@router.get("/event/{str:id}/detail", tags=["HRSC"], response=HrscEventScheme)
@decorate_view(cache_page(CACHE_TIMEOUT))
def event_by_id(request: HttpRequest, id: int):
  """Returns the event details including footprint"""
  return HrscEvent.objects.get(id=id).to_dict(include_foorprint_blob=True)


# removed this endpoint, not efficient enough
# @router.get("/events/{str:collection_key}", tags=["HRSC"], response=List[HrscEventScheme])
# @decorate_view(cache_page(CACHE_TIMEOUT))
# def events_by_collection(request: HttpRequest, collection_key: str):
#  """Returns a list of events inside this collection"""
#  return [event.to_dict() for event in HrscEventCollection.objects.get(key=collection_key).hrscevent_set.all()]


@router.get("/events/winterstorm/filter", tags=["HRSC"], response=List[HrscEventScheme])
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


@router.get("/events/{str:collection_key}/filter", tags=["HRSC"], response=List[HrscEventScheme])
@decorate_view(cache_page(CACHE_TIMEOUT))
def events_by_collection_filter(
  request: HttpRequest,
  collection_key: str,
  longitude: float = None,
  latitude: float = None,
  radius: float = 1000,
  limit: int = 100,
):
  """Filter events by location, radius and parameters"""

  events = HrscEvent.getByLocation(
    point=None,
    longitude=longitude,
    latitude=latitude,
    radius=radius,
    limit=limit,
    event_filter=HrscEventCollection.objects.get(key=collection_key).event_set.all(),
  )

  for key in request.GET.keys():
    if not key.startswith("metadata_"):
      continue

    meta_list = list()
    for value in request.GET.getlist(key):
      metadata_key = key.replace("metadata_", "")

      if metadata_key.endswith("__max"):
        metadata_key = metadata_key.replace("__max", "")
        # we assume only one parameter is set here

        metadata = HrscEventMetadata.objects.get(key=metadata_key)

        if metadata.type == "float":
          metadata_values = HrscEventMetadataValueFloat.objects.filter(
            metadata=metadata, value__lte=value
          )
          events = events.filter(HrscEventMetadataValueFloat__in=metadata_values)

      elif metadata_key.endswith("__min"):
        metadata_key = metadata_key.replace("__min", "")
        # we assume only one parameter is set here

        metadata = HrscEventMetadata.objects.get(key=metadata_key)

        if metadata.type == "float":
          metadata_values = HrscEventMetadataValueFloat.objects.filter(
            metadata=metadata, value__gte=value
          )
          events = events.filter(HrscEventMetadataValueFloat__in=metadata_values)
      else:
        meta_list.append(HrscEventMetadata.objects.get(key=metadata_key))

    if len(meta_list) > 0:
      for metadata in meta_list:
        if metadata.type == "float":
          metadata_values = HrscEventMetadataValueFloat.objects.filter(metadata=metadata, value=value)
          events = events.filter(HrscEventMetadataValueFloat__in=metadata_values)
        elif metadata.type == "string":
          metadata_values = HrscEventMetadataValueString.objects.filter(
            metadata=metadata, value=value
          )
          events = events.filter(HrscEventMetadataValueString__in=metadata_values)

  return [event.to_dict() for event in events]

