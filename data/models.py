import json
import math
import numbers
import re
from typing import Dict, Optional, Tuple

from django.db import models
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe

_json_script_escapes = {
  ord(">"): "\\u003E",
  ord("<"): "\\u003C",
  ord("&"): "\\u0026",
}

# Fields from original dataset that don't need to be displayed
hidden_fields = set(
  [
    "id",
    "rowNum",
    "ID_set",
    "Y_vals",
    "Name",
    "Risk_Component",
    "Category",
    "Local_Path",
    "FileName",
    "Geographic_Relevance_Score",
    "scale_applicability",
    "applicability_notes",
    "urban_rural",
    "Material_Technology2",
    "Material._Properties",
    "Retrofit",
    "Date_of_Construction_or_Retrofit._value",
    "Storey_.Below_Ground",
    "Storeys_Below_Ground_value",
    "Storeys_Below_Ground_lower_bound_value",
    "Storeys_Below_Ground_upper_bound_value",
    "Height_of_ground_floor_above_grade",
    "Height_of_ground_floor_above_grade_lower_bound_value",
    "Height_of_ground_floor_above_grade_upper_bound_value",
    "Slope_of_ground_in_deg",
    "Exterior_Walls",
    "Roof_Shape",
    "Roof_Covering",
    "Roof_System_Type",
    "Roof_Connections_Diaphragm",
    "Roof_Connections._Tie_Down",
    "Floor_System_Type",
    "Floor_Connections",
    "Foundation._System",
    "Position_in_Block",
    "Spatial_Building_Density",
    "Shape_of_Building._Plan",
    "Structural_Irregularity",
    "Primary_Irregularity",
    "Primary_Irregularity_Details",
    "Secondary._Irregularity",
    "Secondary_Irregularity_Details",
    "FloorArea",
    "FloorArea_units",
    "Damage_Estimation_Scale",
    "Loss_Definition",
    "im_sim_type",
    "Method_of_Uncertainty_Propagation",
    "Uncertainty_in_Capacity",
    "Mechanical_Variables",
    "No_of_Distinct_Structural_Models_Analysed",
    "Geometrical_Variables",
    "Structural_Variables",
    "Modelling_Variables",
    "Uncertainty_in_Demand",
    "Use_case_information",
    "Expert_Elicitation_Technique",
    "No_of_Experts",
    "Statistical_Model_Fitting._Method",
    "is_acceptable",
    "is_validated",
    "Function_Relationship",
    "Function_Type",
    "Function_Shape",
    "DS_No",
    "Damage_State_Description",
    "Number_of_Events",
    "Year_Oldest.Event",
    "Year_Newest_Event",
    "Sample_Size",
    "No_of_Data_Points",
    "max_No_of_Data_Points",
    "T_Type",
    "T_in_s",
    "Duplicated",
    "IM_units",
    "Wind_Speed_Height",
    "minimum_im",
    "maximum_im",
    "Mean",
    "Log_Mean",
    "Log_Median",
    "Log_SD",
    "Further_information_on_Dependent_Variable",
    "SD_Y",
    "SD_Y_Description",
    "len_IM",
    "len_IM_c",
    "len_Y_vals",
    "error?",
    "Y_Vals",
    "IM_vals",
    "IM_harmonised",
    "values_xy",
    "metadata",
  ]
)

field_labels_map = {
  "con_description_1": "Construction type 1",
  "con_description_2": "Construction type 2",
  "con_description_3": "Construction type 3",
  "occ_description_1": "Occupation type 1",
  "occ_description_2": "Occupation type 2",
  "occ_description_3": "Occupation type 3",
  "myriad_sectors_applicable": "Sectors",
}


def get_curve_field_label(key: str) -> str:
  label = field_labels_map.get(key, key[0].upper() + key[1:])
  label = re.sub(r"[_\.]+", " ", label)
  label = re.sub(r"\bIm\b", "IM", label)
  label = re.sub(r"\bSd\b", "SD", label)
  return label


class Country(models.Model):
  country_code = models.TextField(unique=True)
  label = models.TextField()

  class Meta:
      ordering = ['label']

  @classmethod
  def ensure_creation_by_iso(cls, code_iso: str, country_dict_by_iso: Dict[str, Dict[str, str]]):
    code = country_dict_by_iso[code_iso]["code_2alpha"]
    country, _ = cls.objects.get_or_create(
      country_code=code, defaults={"label": country_dict_by_iso[code_iso]["name_short"]}
    )

    return country

  def to_dict(self):
    return {
      "country_code": self.country_code,
      "label": self.label,
    }

  def __str__(self):
    return "[" + self.country_code + "] " + str(self.label)


class Nuts2Area(models.Model):
  country = models.ForeignKey(Country, on_delete=models.CASCADE)
  key = models.TextField(unique=True)
  label = models.TextField()

  bbox_min_x = models.FloatField()
  bbox_min_y = models.FloatField()
  bbox_max_x = models.FloatField()
  bbox_max_y = models.FloatField()

  geom_json = models.JSONField()

  def to_dict(self, include_geom_json: bool = False):
    data = {
      "country": self.country.to_dict(),
      "key": self.key,
      "label": self.label,
      "bbox": (
        self.bbox_min_x,
        self.bbox_min_y,
        self.bbox_max_x,
        self.bbox_max_y,
      ),
    }

    if include_geom_json:
      data["geom_json"] = self.geom_json

    return data

  def __str__(self):
    return str(self.country) + " / [" + self.key + "] " + str(self.label)

  @classmethod
  def ensure_creation(
    cls,
    nuts2_key: str,
    country_code: str,
    nuts2_label: str,
    country_label: str,
    bbox: Tuple[str],
    geom_json: dict,
  ):
    country, created_country = Country.objects.get_or_create(
      country_code=country_code, defaults={"label": country_label}
    )

    nuts2area, created_nuts = Nuts2Area.objects.get_or_create(
      key=nuts2_key,
      defaults={
        "label": nuts2_label,
        "country": country,
        "bbox_min_x": bbox[0],
        "bbox_min_y": bbox[1],
        "bbox_max_x": bbox[2],
        "bbox_max_y": bbox[3],
        "geom_json": geom_json,
      },
    )

    if created_country:
      print("created country " + str(country))

    if created_nuts:
      print("created nuts2area " + str(nuts2area))

    return nuts2area


class DataTableMetadata(models.Model):
  key = models.TextField(unique=True)
  source_metadata = models.JSONField(null=True, blank=True)

  def to_dict(self):
    return {
      "key": self.key,
      "source_metadata": self.source_metadata,
    }

  def __str__(self):
    return "[" + self.key + "]"


class KeyLabelSelection:
  @classmethod
  def get_or_create_by_label(cls, label: str, slug_key: Optional[str] = None, **kwargs):
    if label is None:
      return None

    if slug_key is None:
      slug_key = slugify(label)

    instance, created = cls.objects.get_or_create(key=slug_key, defaults={"label": label} | kwargs)

    return instance

  def to_dict(self):
    return {
      "key": self.key,
      "label": self.label,
    }

  def __str__(self):
    return str(self.label)


class TableMetaHazard(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()
  unit = models.TextField(null=True, blank=True)

  def to_dict(self):
    return {
      "key": self.key,
      "label": self.label,
      "unit": self.unit,
    }


class TableMetaExposure(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()
  unit = models.TextField(null=True, blank=True)

  def to_dict(self):
    return {
      "key": self.key,
      "label": self.label,
      "unit": self.unit,
    }


class TableMetaThreshold(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class TableMetaReturnPeriod(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class DataTableColumn(models.Model):
  data_table = models.ForeignKey(DataTableMetadata, on_delete=models.CASCADE)
  key = models.TextField(unique=True)
  label = models.TextField()
  description = models.TextField()

  hazard = models.ForeignKey(TableMetaHazard, on_delete=models.CASCADE)
  exposure = models.ForeignKey(TableMetaExposure, on_delete=models.CASCADE, null=True, blank=True)
  threshold = models.ForeignKey(TableMetaThreshold, on_delete=models.CASCADE, null=True, blank=True)
  return_period = models.ForeignKey(
    TableMetaReturnPeriod, on_delete=models.CASCADE, null=True, blank=True
  )

  def to_dict(self, flat=True):
    if flat:
      return {
        "data_table_id": self.data_table_id,
        "key": self.key,
        "label": self.label,
        "description": self.description,
        "hazard": self.hazard_id,
        "exposure": self.exposure_id,
        "threshold": self.threshold_id,
        "return_period": self.return_period_id,
      }

    return {
      "data_table": self.data_table.to_dict(),
      "key": self.key,
      "label": self.label,
      "description": self.description,
      "hazard": self.hazard.to_dict(),
      "exposure": self.exposure.to_dict(),
      "threshold": self.threshold.to_dict() if self.threshold else None,
      "return_period": self.return_period.to_dict() if self.return_period else None,
    }

  def __str__(self):
    return str(self.data_table) + " / [" + self.key + "] " + str(self.label)


class DataTableColumnValue(models.Model):
  data_table_column = models.ForeignKey(DataTableColumn, on_delete=models.CASCADE)
  nuts_area = models.ForeignKey(Nuts2Area, on_delete=models.CASCADE)

  value = models.FloatField()

  class Meta:
    unique_together = ("data_table_column", "nuts_area")


class CurveHazard(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class CurveQuality(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class CurveConstructionType1(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class CurveConstructionType2(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class CurveConstructionType3(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class CurveOccupancyType1(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class CurveOccupancyType2(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class CurveOccupancyType3(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class CurveCoverage(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class CurveSector(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True)
  label = models.TextField()


class VulnerabilityCurve(models.Model, KeyLabelSelection):
  key = models.TextField(unique=True, max_length=256)
  label = models.TextField()

  hazard = models.ForeignKey(CurveHazard, on_delete=models.CASCADE)
  quality = models.ForeignKey(CurveQuality, on_delete=models.CASCADE, null=True, blank=True)
  con_description_1 = models.ForeignKey(
    CurveConstructionType1, on_delete=models.CASCADE, null=True, blank=True
  )
  con_description_2 = models.ForeignKey(
    CurveConstructionType2, on_delete=models.CASCADE, null=True, blank=True
  )
  con_description_3 = models.ForeignKey(
    CurveConstructionType3, on_delete=models.CASCADE, null=True, blank=True
  )
  occ_description_1 = models.ForeignKey(
    CurveOccupancyType1, on_delete=models.CASCADE, null=True, blank=True
  )
  occ_description_2 = models.ForeignKey(
    CurveOccupancyType2, on_delete=models.CASCADE, null=True, blank=True
  )
  occ_description_3 = models.ForeignKey(
    CurveOccupancyType3, on_delete=models.CASCADE, null=True, blank=True
  )
  coverage = models.ForeignKey(CurveCoverage, on_delete=models.CASCADE)
  myriad_sectors_applicable = models.ManyToManyField(CurveSector)
  countries = models.ManyToManyField(Country)

  metadata = models.JSONField()

  values_xy = models.JSONField()

  def to_dict(self):
    all_vals = {
      "key": self.key,
      "label": self.label,
      "hazard": self.hazard.key,
      "quality": self.quality.key if self.quality else None,
      "con_description_1": self.con_description_1.key if self.con_description_1 else None,
      "con_description_2": self.con_description_2.key if self.con_description_2 else None,
      "con_description_3": self.con_description_3.key if self.con_description_3 else None,
      "occ_description_1": self.occ_description_1.key if self.occ_description_1 else None,
      "occ_description_2": self.occ_description_2.key if self.occ_description_2 else None,
      "occ_description_3": self.occ_description_3.key if self.occ_description_3 else None,
      "coverage": self.coverage.key if self.coverage else None,
      "myriad_sectors_applicable": [s.key for s in self.myriad_sectors_applicable.all()],
      "countries": [c.country_code for c in self.countries.all()],
      "values_xy": self.values_xy,
    } | self.metadata
    return all_vals

  def to_json(self):
    return mark_safe(json.dumps(self.to_dict(), indent=2).translate(_json_script_escapes))

  def get_details_map(self):
    allowed_keys = filter(
      lambda k: not (k.startswith("_") or k in hidden_fields),
      [*self.__dict__.keys(), *self.metadata.keys()],
    )
    details = {}
    for key in allowed_keys:
      # For relationships, show the object not the ID
      if key.endswith("_id"):
        key = re.sub(r"_id$", "", key)
      val = getattr(self, key, None) or getattr(self.metadata, key, None)
      if (
        val is not None
        and val != ""
        and val != "nan"
        and not (isinstance(val, numbers.Number) and math.isnan(val))
      ):
        # Don't display years as decimals
        if key == "Year_Study":
          val = int(val)
        # Convert to readable metadata titles
        label = get_curve_field_label(key)

        display = (
          re.sub(r"(_x000D_|\n)+", "\n\n", val).replace("_", " ").replace(".", " ")
          if isinstance(val, str)
          else ", ".join(val)
          if isinstance(val, list)
          else getattr(val, "label")
          if (isinstance(val, models.Model) and hasattr(val, "label"))
          else ", ".join([a.label for a in val.all()])
          if hasattr(val, "all")
          else val
        )
        if isinstance(val, models.Model) and hasattr(val, "key"):
          val = val.key

        details[key] = {
          "key": key,
          "label": label,
          "display": display,
          "value": val,
        }

    return details

  def get_curve_structures(self):
    pair_of_arrays = list([list(a) for a in zip(*self.values_xy)])
    return [
      {
        "key": "array_pairs",
        "label": "Array of X, Y pairs",
        "value": self.values_xy,
        "format": "json",
        "filename": self.key + " (pairs).json",
      },
      {
        "key": "pair_arrays",
        "label": "X, Y pair of arrays",
        "value": pair_of_arrays,
        "format": "json",
        "filename": self.key + " (arrays).json",
      },
      {
        "key": "csv_xy",
        "label": "CSV with X, Y columns",
        "value": "x,y\n" + "\n".join([",".join(map(str, pair)) for pair in self.values_xy]),
        "format": "csv",
        "filename": self.key + " (x,y).csv",
      },
      {
        "key": "json",
        "label": "JSON with metadata",
        "value": self.to_json(),
        "format": "json",
        "filename": self.key + " (complete).json",
      },
    ]
