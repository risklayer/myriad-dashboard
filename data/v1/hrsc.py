import math
from json import dumps
from typing import List, NoReturn

from django.shortcuts import get_object_or_404
import numpy as np
import rasterio
from dashboard.settings import API_CACHE_TIMEOUT
from data.api_shared import CountriesEnum
from data.models import (
  HrscEvent,
  HrscEventCollection,
  HrscEventMetadata,
  HrscEventMetadataValueFloat,
  HrscEventMetadataValueString,
  HrscExposure,
  HrscExposureRaster,
  HrscHazardProbabilityRaster,
  HrscScenario,
  HrscScenarioExposureVulnerabilityMapping,
  HrscValueCoordinateWinterstorm,
  Nuts3Area,
)
from data.schemas import (
  HrscEventCollectionSchema,
  HrscEventSchema,
  HrscExposureSchema,
  HrscHazardProbabilityRasterSchema,
  HrscScenarioSchema,
)
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance as DBDistance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance as MDistance
from django.db.models import Q
from django.http import HttpRequest
from django.views.decorators.cache import cache_page
from ninja import Query, Router
from ninja.decorators import decorate_view
from ninja.errors import HttpError
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from shapely import from_geojson, geometry

router = Router(tags=["HRSC"])


def error_handler(code, message) -> NoReturn:
  if settings.DEBUG:
    raise Exception(message)
  raise HttpError(code, message)


@router.get("/scenarios", tags=["HRSC"], response=List[HrscScenarioSchema])
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def scenarios(request: HttpRequest):
  """Returns a list of available Scenarios"""
  return [scenario.to_dict() for scenario in HrscScenario.objects.all()]


@router.get("/scenario/calculate_impact/{str:exposure_key}", tags=["HRSC"], response=dict)
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def calculate_impact(
  request: HttpRequest,
  exposure_key: str,
  event_ids: List[int] = Query([]),
  countries: List[CountriesEnum] = Query([]),
  bbox: str | None = None,
  include_geometry: bool = True,
):
  """calculate the risk footprint for a given scenario and exposure, returns a geojson"""
  exposure = HrscExposure.objects.get(key=exposure_key)

  exposure_raster_dbobj = HrscExposureRaster.objects.get(exposure=exposure)

  bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = bbox.split(",")
  bbox_min_x = float(bbox_min_x)
  bbox_min_y = float(bbox_min_y)
  bbox_max_x = float(bbox_max_x)
  bbox_max_y = float(bbox_max_y)

  event_bbox_min_x = None
  event_bbox_min_y = None
  event_bbox_max_x = None
  event_bbox_max_y = None

  all_events: List[HrscEvent] = list()

  grid_resolution_x = 0.1
  grid_resolution_y = 0.1

  use_event_bbox = True
  found_event_bbox = False

  for this_event_id in event_ids:
    event = HrscEvent.objects.get(id=this_event_id)

    if event.footprint_type == "none":
      error_handler(
        404,
        f"Event footprint needed in order to calculate risk. The selected event {event.label} does not include a footprint.",
      )

    if event.footprint_type == "lazy_py_geojson":
      error_handler(
        404,
        f"Event footprint needed in order to calculate risk. The selected event {event.label} has a footprint type that is not currently implemented.",
      )

    all_events.append(event)

    if event.footprint_type == "tiff_embed" or event.footprint_type == "tiff_ext":
      with MemoryFile(event.get_footprint()) as memfile:
        with memfile.open() as src:
          grid_resolution_x = min(grid_resolution_x, src.transform.a)
          grid_resolution_y = min(grid_resolution_y, -src.transform.e)

          event_bbox_min_x = (
            src.bounds.left if event_bbox_min_x is None else min(event_bbox_min_x, src.bounds.left)
          )
          event_bbox_min_y = (
            src.bounds.bottom
            if event_bbox_min_y is None
            else min(event_bbox_min_y, src.bounds.bottom)
          )
          event_bbox_max_x = (
            src.bounds.right
            if event_bbox_max_x is None
            else max(event_bbox_max_x, src.bounds.right)
          )
          event_bbox_max_y = (
            src.bounds.top if event_bbox_max_y is None else max(event_bbox_max_y, src.bounds.top)
          )
          found_event_bbox = True
    elif event.footprint_type == "lazy_py_coord_vals":
      use_event_bbox = False
      pass  # skip this, will not adjust bbox
    else:
      error_handler(
        404,
        f"Event footprint needed in order to calculate risk. The selected event {event.label} has a footprint type that is not recognised.",
      )

  if use_event_bbox and found_event_bbox:
    bbox_min_x = event_bbox_min_x
    bbox_max_x = event_bbox_max_x
    bbox_min_y = event_bbox_min_y
    bbox_max_y = event_bbox_max_y

  nuts3area_filter = Nuts3Area.objects.all()

  if len(countries) > 0 and "ALL" not in countries:
    nuts3area_filter = nuts3area_filter.filter(country__country_code__in=countries)

  nuts3area_filter_bboxed = nuts3area_filter.filter(
    bbox_min_x__lt=bbox_max_x,
    bbox_min_y__lt=bbox_max_y,
    bbox_max_x__gt=bbox_min_x,
    bbox_max_y__gt=bbox_min_y,
  )

  area_bbox_min_x = None
  area_bbox_max_x = None
  area_bbox_min_y = None
  area_bbox_max_y = None

  # Find the bounding box of all selected areas
  areas_found = False
  for area in nuts3area_filter_bboxed:
    areas_found = True
    area_bbox_min_x = (
      area.bbox_min_x if area_bbox_min_x is None else min(area_bbox_min_x, area.bbox_min_x)
    )
    area_bbox_min_y = (
      area.bbox_min_y if area_bbox_min_y is None else min(area_bbox_min_y, area.bbox_min_y)
    )
    area_bbox_max_x = (
      area.bbox_max_x if area_bbox_max_x is None else max(area_bbox_max_x, area.bbox_max_x)
    )
    area_bbox_max_y = (
      area.bbox_max_y if area_bbox_max_y is None else max(area_bbox_max_y, area.bbox_max_y)
    )

  if areas_found:
    # Expand bbox to include all areas overlapping the events/provided bbox
    bbox_min_x = area_bbox_min_x  # type: ignore
    bbox_min_y = area_bbox_min_y  # type: ignore
    bbox_max_x = area_bbox_max_x  # type: ignore
    bbox_max_y = area_bbox_max_y  # type: ignore

  # Expand bbox slightly to a uniform grid based on the resolution
  # This is done to make results for each area deterministic
  bbox_min_x = math.floor(bbox_min_x / grid_resolution_x) * grid_resolution_x
  bbox_max_x = math.ceil(bbox_max_x / grid_resolution_x) * grid_resolution_x
  bbox_min_y = math.floor(bbox_min_y / grid_resolution_y) * grid_resolution_y
  bbox_max_y = math.ceil(bbox_max_y / grid_resolution_y) * grid_resolution_y

  nuts3area_filter = nuts3area_filter_bboxed

  bbox_to_use = bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y

  result_transform = from_origin(bbox_min_x, bbox_max_y, grid_resolution_x, grid_resolution_y)

  steps_y = math.ceil((bbox_max_y - bbox_min_y) / grid_resolution_y)
  steps_x = math.ceil((bbox_max_x - bbox_min_x) / grid_resolution_x)

  impact_data_min = np.zeros((steps_y, steps_x))
  impact_data_max = np.zeros((steps_y, steps_x))

  exposure_raster, _ = exposure_raster_dbobj.get_window(
    bbox_to_use,
    transform_target=result_transform,
    resolution=(steps_y, steps_x),
  )

  exceeded_max_grid = np.zeros((steps_y, steps_x), dtype=bool)

  all_vulnerability_curves = list()

  for event in all_events:
    impact_value_grid = np.zeros((steps_y, steps_x), dtype=np.float32)

    scenario = HrscScenario.objects.get(hazard=event.collection.hazard)

    vulnerability_mapping = HrscScenarioExposureVulnerabilityMapping.objects.filter(
      scenario=scenario, exposure=exposure
    ).first()

    if vulnerability_mapping is None:
      return error_handler(
        404,
        f"No vulnerability curve mapping is available for {scenario.label} hazard scenario and exposure {exposure.label}",
      )

    vulnerability_curve = vulnerability_mapping.vulnerability

    all_vulnerability_curves.append(vulnerability_curve)

    if event.footprint_type == "tiff_embed" or event.footprint_type == "tiff_ext":
      with MemoryFile(event.get_footprint(bbox_to_use)) as memfile, memfile.open() as memfile_image:
        raster = memfile_image.read(1)

        memfile_band = np.empty((steps_y, steps_x), dtype=raster.dtype)
        reproject(
          raster,
          destination=memfile_band,
          src_transform=memfile_image.transform,
          src_crs=CRS.from_epsg(4326),  # WGS84
          dst_transform=result_transform,
          dst_crs=CRS.from_epsg(4326),  # WGS84
          resampling=Resampling.average,
        )

        for pos_y in range(steps_y):
          for pos_x in range(steps_x):
            memfile_value = memfile_band[pos_y][pos_x]

            impact_value, exceeded_max = vulnerability_curve.apply_curve(memfile_value)

            if exceeded_max:
              exceeded_max_grid[pos_y][pos_x] = True

            val = exposure_raster[pos_y][pos_x]
            if np.isnan(val):
              val = 0

            impact_value_grid[pos_y][pos_x] += val * impact_value

    elif event.footprint_type == "lazy_py_geojson":
      error_handler(
        404,
        f"The selected event ({event.label}) has a footprint type that is not currently implemented.",
      )
    elif event.footprint_type == "lazy_py_coord_vals":
      footprint_location_dict = dict()
      for location_x, location_y, value in event.get_footprint(bbox_to_use):
        exposure_row, exposure_col = rasterio.transform.rowcol(result_transform, location_x, location_y)

        if (exposure_row, exposure_col) not in footprint_location_dict:
          footprint_location_dict[(exposure_row, exposure_col)] = []

        footprint_location_dict[(exposure_row, exposure_col)].append(value)

      footprint_value_dict = dict()

      for coord, values in footprint_location_dict.items():
        footprint_value_dict[coord] = sum(values) / len(values)

      for pos_y in range(steps_y):
        for pos_x in range(steps_x):
          if (pos_x, pos_y) in footprint_value_dict:
            impact_value, exceeded_max = vulnerability_curve.apply_curve(
              footprint_value_dict[(pos_x, pos_y)]
            )

            if exceeded_max:
              exceeded_max_grid[pos_y][pos_x] = True

            val = exposure_raster[pos_x][pos_y]
            if np.isnan(val):
              val = 0
            impact_value_grid[pos_y][pos_x] += val * impact_value

    else:
      error_handler(404, "The selected event has a footprint type that is not recognised.")

    for pos_y in range(steps_y):
      for pos_x in range(steps_x):
        impact_value = impact_value_grid[pos_y][pos_x]

        impact_data_min[pos_y][pos_x] = max(impact_data_min[pos_y][pos_x], impact_value)
        impact_data_max[pos_y][pos_x] += impact_value

  # lets limit exposure to maximum
  for pos_y in range(steps_y):
    for pos_x in range(steps_x):
      exposure_value = exposure_raster[pos_y][pos_x]
      if np.isnan(exposure_value):
        exposure_value = 0
      impact_data_max[pos_y][pos_x] = min(
        exposure_value, impact_data_max[pos_y][pos_x]
      )  # limit to max exposure

  areas_dict = {
    area.key: {
      "instance": area,
      "impact_data_min": 0,
      "impact_data_max": 0,
      "exposure_total": 0,
      "exceeded_curve_max": False,
    }
    for area in nuts3area_filter
  }

  num_areas_found = np.zeros((steps_y, steps_x), dtype="int")
  memfile_xy_raster = [
    [rasterio.transform.xy(result_transform, pos_y, pos_x) for pos_x in range(steps_x)]
    for pos_y in range(steps_y)
  ]

  for area in nuts3area_filter:
    area_geojson_obj = from_geojson(dumps(area.geom_json))
    for pos_y in range(steps_y):
      for pos_x in range(steps_x):
        memfile_x, memfile_y = memfile_xy_raster[pos_y][pos_x]
        if (
          area.bbox_min_x < memfile_x
          and area.bbox_min_y < memfile_y
          and area.bbox_max_x > memfile_x
          and area.bbox_max_y > memfile_y
        ):
          point = geometry.Point(memfile_x, memfile_y)
          if area_geojson_obj.contains(point):
            num_areas_found[pos_y][pos_x] += 1
            areas_dict[area.key]["impact_data_min"] += impact_data_min[pos_y][pos_x]
            areas_dict[area.key]["impact_data_max"] += impact_data_max[pos_y][pos_x]
            areas_dict[area.key]["exceeded_curve_max"] = (
              True if exceeded_max_grid[pos_y][pos_x] else False
            )
            areas_dict[area.key]["exposure_total"] += float(exposure_raster[pos_y][pos_x])

  if settings.DEBUG:
    matched = 0
    for pos_y in range(steps_y):
      for pos_x in range(steps_x):
        if num_areas_found[pos_y][pos_x] == 1:
          matched += 1

    print("match ratio: " + str(matched / (steps_y * steps_x)))

  references = sorted(
    list(
      set(
        [
          *(exposure.references or list()),
          # *[reference for curve in all_vulnerability_curves for reference in curve.references],
          # *[reference for event in all_events for reference in (event.references or list())],
        ]
      )
    )
  )

  result = {
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
          "exceeded_curve_max": area_info["exceeded_curve_max"],
          "exposure_total": area_info["exposure_total"],
          "impact_data_min_relative": area_info["impact_data_min"] / area_info["exposure_total"]
          if area_info["exposure_total"]
          else 0,
          "impact_data_max_relative": area_info["impact_data_max"] / area_info["exposure_total"]
          if area_info["exposure_total"]
          else 0,
          "references": references,
        },
        "geometry": area_info["instance"].geom_json if include_geometry else None,
      }
      for area_info in areas_dict.values()
    ],
  }
  return result


@router.get("/exposures", tags=["HRSC"], response=List[HrscExposureSchema])
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def exposures(request: HttpRequest):
  """Returns a list of available Exposures"""
  return [exposure.to_dict() for exposure in HrscExposure.objects.all()]


@router.get("/collections", tags=["HRSC"], response=List[HrscEventCollectionSchema])
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def collections(request: HttpRequest):
  """Returns a list of available Collections"""
  return [collection.to_dict() for collection in HrscEventCollection.objects.all()]


@router.get("/event/{str:id}/detail", tags=["HRSC"], response=HrscEventSchema)
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def event_by_id(request: HttpRequest, id: int, bbox: str | None = None):
  """Returns the event details including footprint"""
  return get_object_or_404(HrscEvent, id=id).to_dict(
    include_footprint_blob=True,
    footprint_bbox=bbox.split(",") if bbox and len(bbox) else None,
    include_metadata=True,
  )


# removed this endpoint, not efficient enough
# @router.get("/events/{str:collection_key}", tags=["HRSC"], response=List[HrscEventSchema])
# @decorate_view(cache_page(API_CACHE_TIMEOUT))
# def events_by_collection(request: HttpRequest, collection_key: str):
#  """Returns a list of events inside this collection"""
#  return [event.to_dict() for event in HrscEventCollection.objects.get(key=collection_key).hrscevent_set.all()]


@router.get("/events/winterstorm/filter", tags=["HRSC"], response=List[HrscEventSchema])
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def events_by_collection_filter_ws(
  request: HttpRequest,
  longitude: float = None,
  latitude: float = None,
  radius: float = 1000,
  value__min: float = None,
  value__max: float = None,
  limit: int = 100,
):
  """
  Filter Winterstorm events by location, radius and parameters.
  Due to witnerstorms covering a large and diffuse area, we filter
  by wind speed inside the footprints
  """

  events = get_events_by_collection_filter_ws(
    longitude,
    latitude,
    radius,
    value__min,
    value__max,
    limit,
  )

  return [event.to_dict(include_metadata=True) for event in events]


@router.get("/events/{str:collection_key}/filter", tags=["HRSC"], response=List[HrscEventSchema])
@decorate_view(cache_page(API_CACHE_TIMEOUT))
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
  filters: dict = request.GET

  events = get_events_by_collection_filter(
    collection_key, longitude, latitude, radius, limit, filters
  )

  return [event.to_dict(include_metadata=True) for event in events]


def get_events_by_collection_filter(
  collection_key: str,
  longitude: float = None,
  latitude: float = None,
  radius: float = 1000,
  limit: int = 100,
  filters: dict = dict(),
):
  collection = HrscEventCollection.objects.filter(key=collection_key).first()
  if not collection:
    return HrscEvent.objects.none()

  events = HrscEvent.getByLocation(
    point=None,
    longitude=longitude,
    latitude=latitude,
    radius=radius,
    # limit=limit,
    # event_filter=collection.hrscevent_set,
    event_filter=HrscEvent.objects.filter(collection__key=collection_key),
  )

  for key in filters.keys():
    if not key.startswith("metadata_"):
      continue

    metadata_key = key.replace("metadata_", "")

    if metadata_key.endswith("__max"):
      metadata_key = metadata_key.replace("__max", "")
      # we assume only one parameter is set here

      metadata = HrscEventMetadata.objects.get(key=metadata_key)

      if metadata.type == "float":
        metadata_values = HrscEventMetadataValueFloat.objects.filter(
          metadata=metadata, value__lte=filters[key]
        )
        events = events.filter(hrsceventmetadatavaluefloat__in=metadata_values)

    elif metadata_key.endswith("__min"):
      metadata_key = metadata_key.replace("__min", "")
      # we assume only one parameter is set here

      metadata = HrscEventMetadata.objects.get(key=metadata_key)

      if metadata.type == "float":
        metadata_values = HrscEventMetadataValueFloat.objects.filter(
          metadata=metadata, value__gte=filters[key]
        )
        events = events.filter(hrsceventmetadatavaluefloat__in=metadata_values)
    else:
      metadata = HrscEventMetadata.objects.get(key=metadata_key)

      meta_or = Q(id__in=[])
      for value in filters.getlist(key):
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
          raise HttpError(500, f"The selected event has an unknown metadata type: {metadata.type}")

      events = events.filter(meta_or)

  events = events.order_by("?").prefetch_related(
    "hrsceventmetadatavaluestring_set", "hrsceventmetadatavaluefloat_set"
  )[:limit]
  return events


@router.get(
  "/hazard_probabilities/raster/list",
  tags=["HRSC"],
  response=List[HrscHazardProbabilityRasterSchema],
)
@decorate_view(cache_page(API_CACHE_TIMEOUT))
def hazard_probabilities_raster_list(request: HttpRequest):
  """Return a probability value for a given hazard and severity"""
  return [r.to_dict() for r in HrscHazardProbabilityRaster.objects.all()]


@router.get("/hazard_probabilities/raster/value/{str:hazard_key}", tags=["HRSC"], response=float)
@decorate_view(cache_page(API_CACHE_TIMEOUT))
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


def get_events_by_collection_filter_ws(
  longitude: float,
  latitude: float,
  radius: float = 1000,
  value__min: float | None = None,
  value__max: float | None = None,
  limit: int = 100,
):
  """
  Filter Winterstorm events by location, radius and parameters.
  Due to witnerstorms covering a large and diffuse area, we filter
  by wind speed inside the footprints
  """

  point = Point(longitude, latitude, srid=settings.DEFAULT_SRID)

  values = HrscValueCoordinateWinterstorm.objects.filter(
    event__collection__key="winterstorm",
    location__location__distance_lt=(point, MDistance(km=radius)),
  )

  if value__min:
    values = values.filter(value__gte=value__min)

  if value__max:
    values = values.filter(value__lte=value__max)

  values = list(
    values.annotate(distance=DBDistance("location__location", point, geography=True))
    .order_by("distance")
    .values_list("event_id", flat=True)
    .distinct()[:limit]
  )

  events = HrscEvent.objects.filter(id__in=values)

  return events
