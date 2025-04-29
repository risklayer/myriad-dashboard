from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Query, Router
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
  HrscExposureRaster,
  HrscScenarioExposureVulnerabilityMapping,
  Nuts3Area,
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

import rasterio
from rasterio.io import MemoryFile
import numpy as np
import math

from shapely import geometry
from shapely import from_geojson

from rasterio.transform import from_origin

from json import dumps

router = Router(tags=["HRSC"])


@router.get("/scenarios", tags=["HRSC"], response=List[HrscScenarioSchema])
@decorate_view(cache_page(CACHE_TIMEOUT))
def scenarios(request: HttpRequest):
  """Returns a list of available Scenarios"""
  return [scenario.to_dict() for scenario in HrscScenario.objects.all()]


@router.get("/scenario/calculate_impact/{str:exposure_key}", tags=["HRSC"], response=dict)
@decorate_view(cache_page(CACHE_TIMEOUT))
def calculate_impact(
  request: HttpRequest, exposure_key: str, event_id: List[int] = Query([]), bbox: str = None,
  include_geometry : bool = True
):
  """calculate the risk footprint for a given scenario and exposure, returns a geojson"""
  exposure = HrscExposure.objects.get(key=exposure_key)

  exposure_raster = HrscExposureRaster.objects.get(exposure=exposure)

  event_bbox_min_x, event_bbox_min_y, event_bbox_max_x, event_bbox_max_y = bbox.split(",")
  event_bbox_min_x = float(event_bbox_min_x)
  event_bbox_min_y = float(event_bbox_min_y)
  event_bbox_max_x = float(event_bbox_max_x)
  event_bbox_max_y = float(event_bbox_max_y)

  all_events: List[HrscEvent] = list()

  grid_resolution_x = 0.1
  grid_resolution_y = 0.1

  for this_event_id in event_id:
    event = HrscEvent.objects.get(id=this_event_id)

    all_events.append(event)

    if event.footprint_type == "none":
      raise Exception("need a footprint in order to calculate risk")
    elif event.footprint_type == "tiff_embed" or event.footprint_type == "tiff_ext":
      with MemoryFile(event.get_footprint()) as memfile:
        with memfile.open() as src:
          grid_resolution_x = min(grid_resolution_x, src.transform.a)
          grid_resolution_y = min(grid_resolution_y, -src.transform.e)

          event_bbox_min_x = min(event_bbox_min_x, src.bounds.left)
          event_bbox_min_y = min(event_bbox_min_y, src.bounds.bottom)
          event_bbox_max_x = max(event_bbox_max_x, src.bounds.right)
          event_bbox_max_y = max(event_bbox_max_y, src.bounds.top)

    elif event.footprint_type == "lazy_py_geojson":
      raise Exception("footprint type not implemented")
    elif event.footprint_type == "lazy_py_coord_vals":
      pass  # skip this, will not adjust bbox
    else:
      raise Exception("unknown footprint type")

  bbox_to_use = event_bbox_min_x, event_bbox_min_y, event_bbox_max_x, event_bbox_max_y

  result_transform = from_origin(
    event_bbox_min_x, event_bbox_max_y, grid_resolution_x, grid_resolution_y
  )

  steps_y = math.ceil((event_bbox_max_y - event_bbox_min_y) / grid_resolution_y)
  steps_x = math.ceil((event_bbox_max_x - event_bbox_min_x) / grid_resolution_x)

  impact_data_min = np.zeros((steps_y, steps_x))
  impact_data_max = np.zeros((steps_y, steps_x))
  impact_data_avrg_lin = np.zeros((steps_y, steps_x))
  impact_data_avrg_sqrt = np.zeros((steps_y, steps_x))

  exposure_raster, exposure_transform = exposure_raster.get_window(bbox_to_use)

  exceeded_max_grid = np.zeros((steps_y, steps_x), dtype=bool)

  for event in all_events:
    impact_value_grid = np.zeros((steps_y, steps_x), dtype=np.float32)

    scenario = HrscScenario.objects.get(hazard=event.collection.hazard)

    vulnerability_curve = HrscScenarioExposureVulnerabilityMapping.objects.get(
      scenario=scenario, exposure=exposure
    ).vulnerability

    if event.footprint_type == "none":
      raise Exception("need a footprint in order to calculate risk")
    elif event.footprint_type == "tiff_embed" or event.footprint_type == "tiff_ext":
      with MemoryFile(event.get_footprint(bbox_to_use)) as memfile, memfile.open() as memfile_image:
        memfile_band = memfile_image.read(1)

        for pos_y in range(steps_y):
          for pos_x in range(steps_x):
            memfile_x, memfile_y = rasterio.transform.xy(result_transform, pos_y, pos_x)
            memfile_row, memfile_col = rasterio.transform.rowcol(
              memfile_image.transform, memfile_x, memfile_y
            )
            if (
              memfile_row < 0
              or memfile_col < 0
              or memfile_row >= memfile_image.height
              or memfile_col >= memfile_image.width
            ):
              continue

            memfile_value = memfile_band[memfile_row][memfile_col]

            exposure_row, exposure_col = exposure_transform.rowcol(memfile_x, memfile_y)

            impact_value, exceeded_max = vulnerability_curve.apply_curve(memfile_value)

            if exceeded_max:
              exceeded_max_grid[pos_y][pos_x] = True

            impact_value_grid[pos_y][pos_x] = (
              exposure_raster[exposure_row][exposure_col] * impact_value
            )

    elif event.footprint_type == "lazy_py_geojson":
      raise Exception("footprint type not implemented")
    elif event.footprint_type == "lazy_py_coord_vals":
      for location_x, location_y, value in event.get_footprint(bbox_to_use):
        exposure_row, exposure_col = exposure_transform.rowcol(location_x, location_y)

        impact_value, exceeded_max = vulnerability_curve.apply_curve(value)

        if exceeded_max:
          exceeded_max_grid[pos_y][pos_x] = True

        impact_value_grid[pos_y][pos_x] = exposure_raster[exposure_row][exposure_col] * impact_value

    else:
      raise Exception("unknown footprint type")

    for pos_y in range(steps_y):
      for pos_x in range(steps_x):
        impact_value = impact_value_grid[pos_y][pos_x]

        impact_data_min[pos_y][pos_x] = max(impact_data_max[pos_y][pos_x], impact_value)
        impact_data_max[pos_y][pos_x] += impact_value

        impact_data_avrg_lin[pos_y][pos_x] += impact_value
        impact_data_avrg_sqrt[pos_y][pos_x] += impact_value * impact_value

  # lets do the average and limit exposure to maximum
  for pos_y in range(steps_y):
    for pos_x in range(steps_x):
      memfile_x, memfile_y = rasterio.transform.xy(result_transform, pos_y, pos_x)
      exposure_row, exposure_col = exposure_transform.rowcol(memfile_x, memfile_y)
      impact_data_max[pos_y][pos_x] = min(
        exposure_raster[pos_y][pos_x], impact_data_max[pos_y][pos_x]
      )  # limit to max exposure
      impact_data_avrg_lin[pos_y][pos_x] /= len(all_events)
      impact_data_avrg_sqrt[pos_y][pos_x] = math.sqrt(
        impact_data_avrg_sqrt[pos_y][pos_x] / len(all_events)
      )

  nuts3area_filter = Nuts3Area.objects.filter(
    bbox_min_x__lt=event_bbox_max_x,
    bbox_min_y__lt=event_bbox_max_y,
    bbox_max_x__gt=event_bbox_min_x,
    bbox_max_y__gt=event_bbox_min_y,
  )

  areas_dict = {
    area.key: {
      "instance": area,
      "impact_data_min": 0,
      "impact_data_max": 0,
      "impact_data_avrg_lin": 0,
      "impact_data_avrg_sqrt": 0,
      "exceeded_curve_max": False,
    }
    for area in nuts3area_filter
  }

  num_areas_found = np.zeros((steps_y, steps_x), dtype="int")
  memfile_xy_raster = [
    [
      rasterio.transform.xy(result_transform, pos_y, pos_x)
      for pos_x in range(steps_x)
    ]
    for pos_y in range(steps_y)
  ]

  for area in nuts3area_filter:
    area_geojson_obj = from_geojson(dumps(area.geom_json))
    for pos_y in range(steps_y):
      for pos_x in range(steps_x):
        #memfile_x, memfile_y = rasterio.transform.xy(result_transform, pos_y, pos_x)
        memfile_x, memfile_y = memfile_xy_raster[pos_y][pos_x]
        if area.bbox_min_x < memfile_x \
          and area.bbox_min_y < memfile_y \
          and area.bbox_max_x > memfile_x \
          and area.bbox_max_y > memfile_y:

          point = geometry.Point(memfile_x, memfile_y)
          if area_geojson_obj.contains(point):
            num_areas_found[pos_y][pos_x] += 1
            areas_dict[area.key]["impact_data_min"] += impact_data_min[pos_y][pos_x]
            areas_dict[area.key]["impact_data_max"] += impact_data_max[pos_y][pos_x]
            areas_dict[area.key]["impact_data_avrg_lin"] += impact_data_avrg_lin[pos_y][pos_x]
            areas_dict[area.key]["impact_data_avrg_sqrt"] += impact_data_avrg_sqrt[pos_y][pos_x]
            areas_dict[area.key]["exceeded_curve_max"] = (
              True if exceeded_max_grid[pos_y][pos_x] else False
            )

  for pos_y in range(steps_y):
    for pos_x in range(steps_x):
      if num_areas_found[pos_y][pos_x] != 1:
        print(
          "Warning, found "
          + str(num_areas_found[pos_y][pos_x])
          + " matching areas for "
          + str(memfile_x)
          + ","
          + str(memfile_y)
          + ", expected 1."
        )

  return {
    "type": "FeatureCollection",
    "name": "nuts3",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": [
      {
        "type": "Feature",
        "properties": {
          "NUTS_ID": area_info["instance"].key,
          "country_id": area_info["instance"].country.country_code,
          "impact_data_min": area_info["impact_data_min"],
          "impact_data_max": area_info["impact_data_max"],
          "impact_data_avrg_lin": area_info["impact_data_avrg_lin"],
          "impact_data_avrg_sqrt": area_info["impact_data_avrg_sqrt"],
          "exceeded_curve_max": area_info["exceeded_curve_max"],
        },
        "geometry": area_info["instance"].geom_json if include_geometry else None,
      }
      for area_info in areas_dict.values()
    ],
  }


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
