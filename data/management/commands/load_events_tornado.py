import csv
import os
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
from django.core.management.base import BaseCommand


class Command(BaseCommand):
  help = "Add a tornado data set"

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
      "--reference",
      type=str,
      nargs="*",
      action="append",
      help="A string to be saved as a reference, citation. Can be supplied multiple times.",
    )

  def handle(
    self, *args, filename: str, zip_filename: str, reference: List[str], **options
  ):  # , skip_existing: bool
    hazard = Hazard.get_or_create_by_label(label="Tornados", slug_key="tornado")

    collection = HrscEventCollection.get_or_create_by_label(
      slug_key="tornado", label="Collection of Tornados", hazard=hazard, references=reference
    )

    HrscEventMetadata.get_or_create_by_label(
      "start_latitude", "start_latitude", type="float", enable_histogram=False
    )
    HrscEventMetadata.get_or_create_by_label(
      "start_longitude", "start_longitude", type="float", enable_histogram=False
    )
    HrscEventMetadata.get_or_create_by_label(
      "end_latitude", "end_latitude", type="float", enable_histogram=False
    )
    HrscEventMetadata.get_or_create_by_label(
      "end_longitude", "end_longitude", type="float", enable_histogram=False
    )
    HrscEventMetadata.get_or_create_by_label(
      "path_length", "path_length", type="float", enable_histogram=True
    )
    HrscEventMetadata.get_or_create_by_label(
      "path_width", "path_width", type="float", enable_histogram=True
    )
    HrscEventMetadata.get_or_create_by_label(
      "tornado_intensity", "tornado_intensity", type="float", enable_histogram=True
    )
    HrscEventMetadata.get_or_create_by_label(
      "wind_speed", "wind_speed", type="float", enable_histogram=True
    )

    with TemporaryDirectory() as tmpDir:
      file_path_to_load = filename
      if zip_filename:
        file_path_to_load = os.path.join(tmpDir, filename)
        print("opening zip file " + zip_filename)
        with zipfile.ZipFile(zip_filename, "r") as zip_ref:
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
        metadata_reference_dict = dict()
        events_to_create = list()
        event_metadata_to_create = list()
        for row in reader:
          longitude = 0.5 * (float(row.get("start_longitude")) + float(row.get("end_longitude")))
          latitude = 0.5 * (float(row.get("start_latitude")) + float(row.get("end_latitude")))

          event, metadata_values = HrscEvent.create_with_attributes(
            commit=False,
            collection=collection,
            location_lon=longitude,
            location_lat=latitude,
            footprint_type="lazy_py_geojson",
            metadata=row,
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
