from typing import Dict, List, Literal, Optional, Union

from geojson_pydantic import MultiPolygon
from ninja import ModelSchema, Schema

from data.models import (
  Country,
  DataTableColumn,
  DataTableMetadata,
  Hazard,
  HrscEvent,
  HrscEventCollection,
  HrscExposureRaster,
  HrscScenario,
  KeyLabelSelection,
  Nuts3Area,
  TableMetaExposure,
  TableMetaReturnPeriod,
  TableMetaThreshold,
  TourismIndicator,
  HrscHazardProbabilityRaster,
  HrscExposure,
)


class DataTableMetadataSchema(ModelSchema):
  class Meta:
    model = DataTableMetadata
    fields = ["key", "source_metadata"]


class KeyLabelSelectionSchema(Schema):
  class Meta:
    model = KeyLabelSelection
    fields = ["key", "label"]


class HazardSchema(ModelSchema):
  unit: Optional[str] = None

  class Meta:
    model = Hazard
    fields = ["key", "label"]


class TableMetaExposureSchema(ModelSchema):
  class Meta:
    model = TableMetaExposure
    fields = ["key", "label", "unit"]


class TableMetaThresholdSchema(ModelSchema):
  class Meta:
    model = TableMetaThreshold
    fields = ["key", "label"]


class TableMetaReturnPeriodSchema(ModelSchema):
  class Meta:
    model = TableMetaReturnPeriod
    fields = ["key", "label"]


class DataTableColumnSchema(ModelSchema):
  return_period: Optional[TableMetaReturnPeriodSchema] = None
  hazard: Optional[HazardSchema] = None
  exposure: Optional[TableMetaExposureSchema] = None
  threshold: Optional[TableMetaThresholdSchema] = None
  references: Optional[List[str]] = []

  class Meta:
    model = DataTableColumn
    fields = [
      "key",
      "label",
      "description",
    ]


class DataTableColumnsWithFilterOptionsSchema(Schema):
  columns: List[DataTableColumnSchema]
  filter_options: Dict[str, Union[List[Union[str, float]], None]]


class DataTableColumnSummarySchema(ModelSchema):
  class Meta:
    model = DataTableColumn
    fields = [
      "key",
      "label",
      "description",
    ]


class DataTableColumnSummaryWithFilterOptionsSchema(Schema):
  columns: List[DataTableColumnSummarySchema]
  filter_options: Dict[str, List[Union[str, float]] | None]


# class DataTableColumnValueSchema(ModelSchema):
#   class Meta:
#     model = DataTableColumnValue
#     fields = ["TODO"]


# class CurveHazardSchema(ModelSchema):
#   class Meta:
#     model = CurveHazard
#     fields = ["TODO"]


# class CurveQualitySchema(ModelSchema):
#   class Meta:
#     model = CurveQuality
#     fields = ["TODO"]


# class CurveConstructionType1Schema(ModelSchema):
#   class Meta:
#     model = CurveConstructionType1
#     fields = ["TODO"]


# class CurveConstructionType2Schema(ModelSchema):
#   class Meta:
#     model = CurveConstructionType2
#     fields = ["TODO"]


# class CurveConstructionType3Schema(ModelSchema):
#   class Meta:
#     model = CurveConstructionType3
#     fields = ["TODO"]


# class CurveOccupancyType1Schema(ModelSchema):
#   class Meta:
#     model = CurveOccupancyType1
#     fields = ["TODO"]


# class CurveOccupancyType2Schema(ModelSchema):
#   class Meta:
#     model = CurveOccupancyType2
#     fields = ["TODO"]


# class CurveOccupancyType3Schema(ModelSchema):
#   class Meta:
#     model = CurveOccupancyType3
#     fields = ["TODO"]


# class CurveCoverageSchema(ModelSchema):
#   class Meta:
#     model = CurveCoverage
#     fields = ["TODO"]


# class CurveSectorSchema(ModelSchema):
#   class Meta:
#     model = CurveSector
#     fields = ["TODO"]


# class VulnerabilityCurveSchema(ModelSchema):
#   class Meta:
#     model = VulnerabilityCurve
#     fields = ["TODO"]


class CountrySchema(ModelSchema):
  class Meta:
    model = Country
    fields = ["country_code", "label"]


class Nuts3AreaSchema(ModelSchema):
  country: CountrySchema

  class Meta:
    model = Nuts3Area
    fields = [
      "key",
      "label",
      # "bbox_min_x",
      # "bbox_min_y",
      # "bbox_max_x",
      # "bbox_max_y",
      # "geom_json",
    ]


class AreaPropertiesSchema(Schema):
  NUTS_ID: str
  country_code: str


type AreaValuesWithColumnsSchema = Dict[str, float | str] | AreaPropertiesSchema


class ShapeFeature(Schema):
  type: Literal["Feature"]
  geometry: MultiPolygon
  # Note: this outputs the correct types in TS, swagger schemas and in the
  # returned results, but doesn't reflect the AreaPropertiesSchema fields in
  # Swagger examples
  properties: AreaValuesWithColumnsSchema


class FeatureCollectionSchema(Schema):
  type: Literal["FeatureCollection"]
  features: List[ShapeFeature]


class HrscScenarioSchema(ModelSchema):
  hazard: str
  event_collection: str
  mapping: Dict[str, str]

  class Meta:
    model = HrscScenario
    fields = ["key", "label", "description", "hazard", "event_collection"]


class HrscEventSchema(ModelSchema):
  collection_id: int
  location: Optional[Dict[str, float]] = None
  footprint_type: str
  footprint: Union[str, dict, None, List] = None
  hazard: Optional[str]
  hazardLabel: Optional[str]
  label: str
  unit: Optional[str] = None
  metadata: Optional[Dict[str, Union[str, float]]] = None
  # references: Optional[List[str]] = []

  class Meta:
    model = HrscEvent
    fields = ["id", "footprint_type", "footprint"]


class HrscEventCollectionSchema(ModelSchema):
  key: str
  label: str
  hazard: HazardSchema

  class Meta:
    model = HrscEventCollection
    fields = ["key", "label"]


class TourismIndicatorSchema(ModelSchema):
  key: str
  label: str

  class Meta:
    model = TourismIndicator
    fields = ["key", "label"]


class HrscHazardProbabilityRasterSchema(ModelSchema):
  severity_unit: str
  hazard: HazardSchema
  severities: List[float]
  references: Optional[List[str]] = []

  class Meta:
    model = HrscHazardProbabilityRaster
    fields = ["severity_unit"]


class HrscExposureRasterSchema(ModelSchema):
  class Meta:
    model = HrscExposureRaster
    fields = ["file_type", "file"]


class HrscExposureSchema(ModelSchema):
  key: str
  label: str
  raster: HrscExposureRasterSchema
  nuts3_column: bool
  references: Optional[List[str]] = []

  class Meta:
    model = HrscExposure
    fields = ["key", "label"]
