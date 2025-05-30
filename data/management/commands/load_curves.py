import pandas
from data.data_region.country_list import get_country_dict_by_iso
from data.models import (
  CurveConstructionType1,
  CurveConstructionType2,
  CurveConstructionType3,
  CurveCoverage,
  Hazard,
  CurveOccupancyType1,
  CurveOccupancyType2,
  CurveOccupancyType3,
  CurveQuality,
  CurveSector,
  VulnerabilityCurve,
  Country,
)
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify
import hashlib
from math import isnan

from data.utils import clear_cache

country_dict_by_iso = get_country_dict_by_iso()


class Command(BaseCommand):
  help = "Load Curves from Excel File"

  def add_arguments(self, parser):
    parser.add_argument("--filename", type=str, required=True)
    parser.add_argument("--sheet", type=str, default="Sheet1")
    parser.add_argument("--clear-existing", dest="clear_existing", action="store_true")

  def handle(self, *args, filename: str, sheet: str, clear_existing: bool, **options):
    data = pandas.read_excel(filename, sheet_name=sheet)

    if clear_existing:
      VulnerabilityCurve.objects.all().delete()

    for index, row in data.iterrows():
      name = row["Name"]
      hazard = row["Hazard"]
      quality = row.get("Quality", "")
      con_description_1 = row.get("Con_Description_1", "")
      con_description_2 = row.get("Con_Description_2", "")
      con_description_3 = row.get("Con_Description_3", "")
      occ_description_1 = row.get("Occ_Description_1", "")
      occ_description_2 = row.get("Occ_Description_2", "")
      occ_description_3 = row.get("Occ_Description_3", "")
      coverage = row["Coverage"]
      myriad_sectors_list = [c.strip() for c in row["MYRIAD_Sectors_Applicable"].split(";")]
      country_list = (
        [c.strip() for c in row.get("Country", "").split(",")] if isinstance(row.get("Country", ""), str) else []
      )
      x_values = row["IM_vals"]
      y_values = row["Y_vals"]
      if isinstance(y_values, (float, int)):
        y_values = row["Y_Vals"]

      if isinstance(x_values, str):
        x_values = [float(val) for val in x_values.split(",")]
      else:
        print("x_values: " + repr(x_values) + " is not a list for " + name)
        x_values = [str(x_values)]

      if isinstance(y_values, str):
        y_values = [float(val) for val in y_values.split(",")]
      else:
        print("y_values: " + repr(y_values) + " is not a list for " + name)
        y_values = [str(y_values)]

      metadata = dict(row)
      metadata.pop("Name")
      metadata.pop("Hazard")
      metadata.pop("Quality", "")
      metadata.pop("Con_Description_1", "")
      metadata.pop("Con_Description_2", "")
      metadata.pop("Con_Description_3", "")
      metadata.pop("Occ_Description_1", "")
      metadata.pop("Occ_Description_2", "")
      metadata.pop("Occ_Description_3", "")
      metadata.pop("Coverage")
      metadata.pop("MYRIAD_Sectors_Applicable")
      metadata.pop("Country", "")
      metadata.pop("IM_vals")
      metadata.pop("Y_vals", "")
      metadata.pop("Y_Vals", "")

      items = metadata.items()
      metadata = {k: str(v) for k, v in items if isinstance(v, str) or not isnan(v)}

      try:
        if isinstance(name, str):
          name = name.strip()
        if isinstance(hazard, str):
          hazard = hazard.strip()
        if isinstance(quality, str):
          quality = quality.strip()
        if isinstance(con_description_1, str):
          con_description_1 = con_description_1.strip()
        if isinstance(con_description_2, str):
          con_description_2 = con_description_2.strip()
        if isinstance(con_description_3, str):
          con_description_3 = con_description_3.strip()
        if isinstance(occ_description_1, str):
          occ_description_1 = occ_description_1.strip()
        if isinstance(occ_description_2, str):
          occ_description_2 = occ_description_2.strip()
        if isinstance(occ_description_3, str):
          occ_description_3 = occ_description_3.strip()
        if isinstance(coverage, str):
          coverage = coverage.strip()

        if not isinstance(hazard, str) and isnan(hazard):
          hazard = None

        if not isinstance(quality, str) and isnan(quality):
          quality = None

        if not isinstance(con_description_1, str) and isnan(con_description_1):
          con_description_1 = None

        if not isinstance(con_description_2, str) and isnan(con_description_2):
          con_description_2 = None

        if not isinstance(con_description_3, str) and isnan(con_description_3):
          con_description_3 = None

        if not isinstance(occ_description_1, str) and isnan(occ_description_1):
          occ_description_1 = None

        if not isinstance(occ_description_2, str) and isnan(occ_description_2):
          occ_description_2 = None

        if not isinstance(occ_description_3, str) and isnan(occ_description_3):
          occ_description_3 = None

        if not isinstance(coverage, str) and isnan(coverage):
          coverage = None

        hazard_instance = Hazard.get_or_create_by_label(hazard)
        quality_instance = CurveQuality.get_or_create_by_label(quality)
        con_description_1_instance = CurveConstructionType1.get_or_create_by_label(
          con_description_1
        )
        con_description_2_instance = CurveConstructionType2.get_or_create_by_label(
          con_description_2
        )
        con_description_3_instance = CurveConstructionType3.get_or_create_by_label(
          con_description_3
        )
        occ_description_1_instance = CurveOccupancyType1.get_or_create_by_label(occ_description_1)
        occ_description_2_instance = CurveOccupancyType2.get_or_create_by_label(occ_description_2)
        occ_description_3_instance = CurveOccupancyType3.get_or_create_by_label(occ_description_3)
        coverage_instance = CurveCoverage.get_or_create_by_label(coverage)
        myriad_sectors_instances = list()
        for sector in myriad_sectors_list:
          myriad_sectors_instances.append(CurveSector.get_or_create_by_label(sector))
        country_instances = list()
        for code in country_list:
          if code in country_dict_by_iso:
            country_instances.append(Country.ensure_creation_by_iso(code, country_dict_by_iso))

        h = hashlib.new("sha3_224")
        h.update(
          (
            str(hazard)
            + str(quality)
            + str(con_description_1)
            + str(con_description_2)
            + str(con_description_3)
            + str(occ_description_1)
            + str(occ_description_2)
            + str(occ_description_3)
            + str(coverage)
            + ",".join(myriad_sectors_list)
            + ",".join(country_list)
          ).encode("utf-8")
        )

        key = h.hexdigest()[0:8] + "-" + slugify(name)

        if occ_description_1 is not None:
          name += " [" + str(occ_description_1) + "]"

        if len(key) > 256:
          raise Exception("key too long")

        curve = VulnerabilityCurve.objects.create(
          key=key,
          label=name,
          hazard=hazard_instance,
          quality=quality_instance,
          con_description_1=con_description_1_instance,
          con_description_2=con_description_2_instance,
          con_description_3=con_description_3_instance,
          occ_description_1=occ_description_1_instance,
          occ_description_2=occ_description_2_instance,
          occ_description_3=occ_description_3_instance,
          coverage=coverage_instance,
          metadata=metadata,
          values_xy=list(zip(x_values, y_values)),
        )
        curve.myriad_sectors_applicable.set(myriad_sectors_instances)
        curve.countries.set(country_instances)
      except Exception as e:
        print("error creating curve " + key + " " + name + " " + repr(e))

    print("Resetting cache")
    clear_cache()
    print("Done")
