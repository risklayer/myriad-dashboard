import csv
import os
import shutil
import zipfile
from tempfile import TemporaryDirectory
from typing import List

from data.models import (
  Hazard,
  HrscEvent,
  HrscEventCollection,
  HrscEventMetadata,
  HrscEventMetadataValueFloat,
)
from data.utils import clear_cache
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
  help = "Earthquake data set"

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
    parser.add_argument(
      "--relative-path",
      type=str,
      required=True,
      dest="relative_path",
      help="The relative path, will be formatted with the ReRun",
    )
    parser.add_argument(
      "--footprint-num-offset",
      type=int,
      required=False,
      default=0,
      dest="footprint_num_offset",
      help="Offset to correctly guess the footprint filename",
    )
    parser.add_argument(
      "--reference",
      type=str,
      nargs="*",
      action="append",
      help="A string to be saved as a reference, citation. Can be supplied multiple times.",
    )

  def handle(
    self,
    *args,
    filename: str,
    zip_filename: str,
    relative_path: str,
    footprint_num_offset: int,
    reference: List[str],
    **options,
  ):
    hazard = Hazard.get_or_create_by_label(label="Earthquakes", slug_key="earthquake")

    collection = HrscEventCollection.get_or_create_by_label(
      slug_key="earthquake", label="Collection of Earthquakes", hazard=hazard, references=reference
    )

    HrscEventMetadata.get_or_create_by_label(
      "Magnitude", "magnitude", type="float", enable_histogram=True
    )

    HrscEventMetadata.get_or_create_by_label("Depth", "depth", type="float", enable_histogram=True)

    HrscEventMetadata.get_or_create_by_label(
      "Strike", "strike", type="float", enable_histogram=False
    )

    HrscEventMetadata.get_or_create_by_label("Dip", "dip", type="float", enable_histogram=False)

    HrscEventMetadata.get_or_create_by_label(
      "RuptureLength", "rupturelength", type="float", enable_histogram=False
    )

    HrscEventMetadata.get_or_create_by_label(
      "RuptureWidth", "rupturewidth", type="float", enable_histogram=False
    )

    #  Skip the following Metadata:
    #  x1
    #  y1
    #  x2
    #  y2
    #  x3
    #  y3
    #  x4
    #  y4
    #  z1
    #  z2
    #  z3
    #  z4
    #  RuptureType
    #  EventType
    #  Source
    #  Rake
    #  Sigma
    #  RandomYear
    #  ReRun
    #  Seed

    with TemporaryDirectory() as tmpDir:
      file_path_to_load = filename
      zip_ref = None
      if zip_filename:
        file_path_to_load = os.path.join(tmpDir, filename)
        print("opening zip file " + zip_filename)
        zip_ref = zipfile.ZipFile(zip_filename, "r")
        with zip_ref.open(filename) as source_file:
          extract_filename = os.path.join(tmpDir, filename)
          os.makedirs(os.path.dirname(extract_filename), exist_ok=True)
          with open(extract_filename, "wb") as output_file:
            print("extracting " + extract_filename)
            output_file.write(source_file.read())

      print("opening " + file_path_to_load)
      with open(file_path_to_load, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        print("creating events")
        events_to_create = list()
        event_metadata_to_create = list()

        metadata_reference_dict = dict()
        for row in reader:
          footprint_number = int(float(row.get("ReRun"))) + footprint_num_offset

          footprint_path_to_load = os.path.dirname(filename) + relative_path.format(
            footprint_number
          )

          subpath_footprint = os.path.join(
            "hrsc", "footprint", "earthquake", os.path.basename(footprint_path_to_load)
          )
          output_file_path = os.path.join(settings.RASTER_DATA_ROOT, subpath_footprint)

          os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

          try:
            if zip_filename:
              with zip_ref.open(footprint_path_to_load) as source_file:
                with open(output_file_path, "wb") as output_file:
                  output_file.write(source_file.read())
            else:
              shutil.copyfile(footprint_path_to_load, output_file_path)
          except Exception as exc:
            print(
              'Error during loading in footprint "'
              + str(zip_filename)
              + '":"'
              + footprint_path_to_load
              + '": '
              + str(exc)
            )
            continue

          event, metadata_values = HrscEvent.create_with_attributes(
            commit=False,
            collection=collection,
            location_lon=float(row.get("Longitude")),
            location_lat=float(row.get("Latitude")),
            footprint_type="tiff_ext",
            footprint=subpath_footprint.encode(encoding="utf-8"),
            metadata={
              "magnitude": float(row.get("Magnitude")),
              "depth": float(row.get("Depth")),
              "strike": float(row.get("Strike")),
              "dip": float(row.get("Dip")),
              "rupturelength": float(row.get("RuptureLength")),
              "rupturewidth": float(row.get("RuptureWidth")),
            },
            metadata_reference_dict=metadata_reference_dict,
          )
          events_to_create.append(event)
          event_metadata_to_create += metadata_values

        print(" bulk creation")
        HrscEvent.objects.bulk_create(events_to_create)
        HrscEventMetadataValueFloat.objects.bulk_create(event_metadata_to_create)
        print("  ... done")

    print("Resetting cache")
    clear_cache()
    print("Done")
