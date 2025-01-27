import math
import numbers
import re
from typing import Dict, Tuple

from django.db import models
from django.template.defaultfilters import slugify


class Country(models.Model):
  country_code = models.TextField(unique=True)
  label = models.TextField()

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

  def to_dict(self):
    return {
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
        "bbox_min_y": bbox[2],
        "bbox_max_x": bbox[1],
        "bbox_max_y": bbox[3],
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


class DataTableColumn(models.Model):
  data_table = models.ForeignKey(DataTableMetadata, on_delete=models.CASCADE)
  key = models.TextField(unique=True)
  label = models.TextField()

  def to_dict(self):
    return {
      "data_table_id": self.data_table_id,
      "key": self.key,
      "label": self.label,
    }

  def __str__(self):
    return str(self.data_table) + " / [" + self.key + "] " + str(self.label)


class DataTableColumnValue(models.Model):
  data_table_column = models.ForeignKey(DataTableColumn, on_delete=models.CASCADE)
  nuts_area = models.ForeignKey(Nuts2Area, on_delete=models.CASCADE)

  value = models.FloatField()

  class Meta:
    unique_together = ("data_table_column", "nuts_area")


class CurveKeyLabelSelection:
  @classmethod
  def get_or_create_by_label(cls, label: str):
    if label is None:
      return None

    slug_key = slugify(label)

    instance, created = cls.objects.get_or_create(key=slug_key, defaults={"label": label})

    return instance

  def to_dict(self):
    return {
      "key": self.key,
      "label": self.label,
    }

  def __str__(self):
    return str(self.label)


class CurveHazard(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class CurveQuality(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class CurveConstructionType1(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class CurveConstructionType2(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class CurveConstructionType3(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class CurveOccupancyType1(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class CurveOccupancyType2(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class CurveOccupancyType3(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class CurveCoverage(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class CurveSector(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True)
  label = models.TextField()


class VulnerabilityCurve(models.Model, CurveKeyLabelSelection):
  key = models.SlugField(unique=True, max_length=256)
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
    return {
      "key": self.key,
      "label": self.label,
      "hazard": self.hazard.key,
      "quality": self.quality.key,
      "con_description_1": self.con_description_1.key,
      "con_description_2": self.con_description_2.key,
      "con_description_3": self.con_description_3.key,
      "occ_description_1": self.occ_description_1.key,
      "occ_description_2": self.occ_description_2.key,
      "occ_description_3": self.occ_description_3.key,
      "coverage": self.coverage.key,
      "myriad_sectors_applicable": [s.key for s in self.myriad_sectors_applicable.all()],
      "countries": [c.country_code for c in self.countries.all()],
      "values_xy": self.values_xy,
    } | self.metadata

  def get_details_map(self):
    displayed_fields = set(
      [
        "MYRIAD_Sectors_Applicable",
        "Name",
        "Taxonomy",
        "Damage_Scale",
        "IM_type",
        "Data_Source",
        "Reference",
        "Risk_Component",
        "Asset",
        "Coverage",
        "Hazard",
        "Authors_Study",
        "Year_Study",
        "Weblink_Study",
        "General_Comments",
        "Region",
        "Country",
        "Quality",
        "Con_Description_1",
        "Con_Description_2",
        "Con_Description_3",
        "Occ_Description_1",
        "Occ_Description_2",
        "Occ_Description_3",
        "Material_Type",
        "Material_Technology1",
        "Material_Technology2",
        "Date_of_Construction_or_Retrofit",
        "LLRS",
        "System_Ductility",
        "Height",
        "Height_value",
        "Height_lower_bound_.value",
        "Height_upper_bound_.value",
        "Storey_.Below_Ground",
        "Storeys_Below_Ground_value",
        "Storeys_Below_Ground_lower_bound_value",
        "Storeys_Below_Ground_upper_bound_value",
        "Height_of_ground_floor_above_grade",
        "Height_of_ground_floor_above_grade_value",
        "Height_of_ground_floor_above_grade_lower_bound_value",
        "Height_of_ground_floor_above_grade_upper_bound_value",
        "Slope_of_ground_in_deg",
        "Exterior_Walls",
        "Roof_Shape",
        "Roof_Covering",
        "Roof_System_Materials",
        "Roof_System_Type",
        "Roof_Connections_Diaphragm",
        "Roof_Connections._Tie_Down",
        "Floor_System_Material",
        "Floor_System_Type",
        "Floor_Connections",
        "Foundation._System",
        "Occupancy_Class",
        "Occupancy_Detail",
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
        "Assessment_Type",
        "Damage_Estimation_Scale",
        "Loss_Definition",
        "EDP",
        "Analysis_Type",
        "Model_Type",
        "IM_Evaluation",
        "im_sim_type",
        "No_of_Distinct_Structural_Models_Analysed",
        "Method_of_Uncertainty_Propagation",
        "Uncertainty_in_Capacity",
        "Mechanical_Variables",
        "Geometrical_Variables",
        "Structural_Variables",
        "Modelling_Variables",
        "Uncertainty_in_Demand",
        "Use_case_information",
        "Expert_Elicitation_Technique",
        "No_of_Experts",
        "Statistical_Model_Fitting._Method",
        "is_acceptable",
        "Statistical_Model",
        "is_validated",
        "Validation_Data_Source",
        "Function_Relationship",
        "Function_Type",
        "Function_Shape",
        "DS_No",
        "Damage_State_Description",
        "Structural_NonStructural",
        "Components_Failure_Mechanism",
        "Damage_to_Loss_function",
        "Damage_to_Loss_function_Uncertainty_Modelling",
        "Source_of_Damage_Data",
        "Number_of_Events",
        "Year_Oldest.Event",
        "Year_Newest_Event",
        "Sample_Size",
        "sample",
        "nonsampling_err",
        "type_nonsampling_err",
        "is_fix_nonsam_err",
        "Isoseismic_Unit",
        "Sources_of.Uncertainty_Explicitely_Modelled",
        "Are_the_Data_Aggregated",
        "No_of_Data_Points",
        "max_No_of_Data_Points",
        "T_Type",
        "T_in_s",
        "Duplicated",
        "IM_units",
      ]
    )

    all_details = self.to_dict()

    details = {}
    for key in all_details.keys():
      val = all_details.get(key)
      if (
        val is not None
        and val != ""
        and val != "nan"
        and key in displayed_fields
        and not (isinstance(val, numbers.Number) and math.isnan(val))
      ):
        # Don't display years as decimals
        if key == "Year_Study":
          val = int(val)
        # Convert to readable metadata titles
        label = (
          key.replace("_", " ")
          .replace("Weblink Study", "Weblink")
          .replace("Con Description", "Construction Type")
          .replace("Occ Description", "Occupancy Type")
          .replace("MYRIAD Sectors Applicable", "Sectors")
        )
        details[key] = {
          "label": label,
          "display": (
            re.sub(r"(_x000D_|\n)+", "\n\n", val).replace("_", " ") if isinstance(val, str) else val
          ),
          "value": val,
        }

    return details

  def get_curve_structures(self):
    pair_of_arrays = list([list(a) for a in zip(*self.values_xy)])
    return [
      {
        "label": "Array of X, Y pairs",
        "value": self.values_xy,
        "format": "json",
        "filename": self.key + " (pairs).json",
      },
      {
        "label": "X, Y pair of arrays",
        "value": pair_of_arrays,
        "format": "json",
        "filename": self.key + " (arrays).json",
      },
      {
        "label": "CSV with X, Y columns",
        "value": "x,y\n" + "\n".join([",".join(map(str, pair)) for pair in self.values_xy]),
        "format": "csv",
        "filename": self.key + " (x,y).csv",
      },
      {
        "label": "JSON with metadata",
        "value": self.to_dict(),
        "format": "json",
        "filename": self.key + " (complete).json",
      },
    ]
