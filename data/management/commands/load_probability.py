from data.models import (
  Hazard,
  HrscHazardProbabilityRaster,
  HrscHazardProbabilityRasterInstance,
)
from django.core.management.base import BaseCommand

from django.conf import settings

import os
import zipfile

import os.path
import shutil

from data.utils import clear_cache


class Command(BaseCommand):
  help = "Load Probability from a raster file"

  def add_arguments(self, parser):
    parser.add_argument(
      "--filename",
      type=str,
      required=True,
      help="path of the file to load OR the file path inside the zip file if --zip-filename is also set.",
    )
    parser.add_argument(
      "--zip-filename",
      type=str,
      required=False,
      dest="zip_filename",
      help="If the file to load is inside an archive, then spcify the archive path with this argument and --filename as the path of the file inside the archive",
    )
    parser.add_argument("--format", type=str, required=True, choices=["tiff"])
    parser.add_argument("--hazard", type=str, required=True, help="<key>:<label>")
    parser.add_argument("--severity", type=str, required=True, help="<value>:<unit>")

  def handle(
    self,
    *args,
    filename: str,
    zip_filename: str,
    format: str,
    hazard: str,
    severity: str,
    **options,
  ):
    hazard_key, hazard_label = hazard.split(":")
    severity_value, severity_unit = severity.split(":")

    hazard = Hazard.get_or_create_by_label(hazard_label, hazard_key)
    raster, _ = HrscHazardProbabilityRaster.objects.get_or_create(
      hazard=hazard, defaults={"severity_unit": severity_unit}
    )

    # remove old one
    HrscHazardProbabilityRasterInstance.objects.filter(
      probability_raster=raster, severity_value=severity_value
    ).delete()

    subpath = (
      os.path.join("hrsc", "probability", hazard_key, severity_unit + "_" + str(severity_value))
      + os.path.splitext(filename)[1]
    )
    output_file_path = os.path.join(settings.RASTER_DATA_ROOT, subpath)

    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

    if zip_filename:
      with zipfile.ZipFile(zip_filename, "r") as zip_ref:
        with zip_ref.open(filename) as source_file:
          with open(output_file_path, "wb") as output_file:
            output_file.write(source_file.read())
    else:
      shutil.copyfile(filename, output_file_path)

    HrscHazardProbabilityRasterInstance.objects.create(
      probability_raster=raster,
      severity_value=severity_value,
      file=subpath,
      file_type=format,
    )

    print("Resetting cache")
    clear_cache()
    print("Done")
