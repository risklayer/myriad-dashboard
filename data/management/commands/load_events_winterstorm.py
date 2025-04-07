from data.models import (
  Hazard,
  HrscEvent,
  HrscEventCollection,
  HrscValueCoordinateWinterstorm,
  HrscEventMetadata,
  HrscEventMetadataValueString,
  GridLocation,
)
from django.core.management.base import BaseCommand

from tempfile import TemporaryDirectory

import os
import zipfile

import csv
from django.contrib.gis.geos import Point

from django.db import transaction


class Command(BaseCommand):
  help = "Add a winterstorm data set"

  def add_arguments(self, parser):
    parser.add_argument(
      "--filename",
      type=str,
      required=True,
      help="path of the file to load OR the file path inside the zip file if --zip-filename is also set.",
    )
    parser.add_argument(
      "--sparse",
      action="store_true",
      help="Only use every 503rd entry to reduce the footprint of the database for testing purposes.",
    )
    parser.add_argument(
      "--zip-filename",
      type=str,
      required=False,
      dest="zip_filename",
      help="If the file to load is inside an archive, then spcify the archive path with this argument and --filename as the path of the file inside the archive",
    )

  def handle(self, *args, filename: str, zip_filename: str, sparse: bool, **options):
    hazard = Hazard.get_or_create_by_label(label="Winter storm", slug_key="winterstorm")

    collection = HrscEventCollection.get_or_create_by_label(
      slug_key="winterstorm", label="Collection of winter storms", hazard=hazard
    )

    label_meta = HrscEventMetadata.get_or_create_by_label(
      label="Event label", slug_key="event_label", type="string", enable_histogram=False
    )

    with TemporaryDirectory() as tmpDir:
      file_path_to_load = filename
      if zip_filename:
        file_path_to_load = os.path.join(tmpDir, filename.lstrip("/"))
        print("opening zip file " + zip_filename)
        with zipfile.ZipFile(zip_filename, "r") as zip_ref:
          with zip_ref.open(filename) as source_file:
            os.makedirs(os.path.dirname(file_path_to_load), exist_ok=True)
            with open(file_path_to_load, "wb") as output_file:
              print("extracting " + file_path_to_load)
              output_file.write(source_file.read())

      events_to_create = list()
      event_metadata_to_create = list()
      events = dict()
      location_dict = dict()

      print("opening " + file_path_to_load)
      with open(file_path_to_load, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        print("creating events")
        sparse_counter = 0
        for fieldname in reader.fieldnames:
          if fieldname in {"Longitude", "Latitude"}:
            continue

          if sparse:
            sparse_counter += 1
            # we are using a prime number here to have some pseudo-randomness in the distribution of the footprint values
            if sparse_counter > 503:
              sparse_counter = 0
            else:
              continue

          event = None

          metadata_filter = HrscEventMetadataValueString.objects.filter(
            metadata=label_meta, value=fieldname
          )
          if metadata_filter.exists():
            event = metadata_filter.get().event
          else:
            event = HrscEvent(
              collection=collection,
              location=None,
              footprint=None,
              footprint_type="lazy_py_coord_vals",
            )
            event_metadata = HrscEventMetadataValueString(
              metadata=label_meta, event=event, value=fieldname
            )

            events_to_create.append(event)
            event_metadata_to_create.append(event_metadata)
          events[fieldname] = event

        HrscEvent.objects.bulk_create(events_to_create)
        HrscEventMetadataValueString.objects.bulk_create(event_metadata_to_create)
        print("  ... done")

        print("creating coordinates")
        with transaction.atomic():
          for row in reader:
            longitude = float(row.pop("Longitude"))
            latitude = float(row.pop("Latitude"))
            location, _ = GridLocation.objects.get_or_create(location=Point(longitude, latitude))
            location_dict[(longitude, latitude)] = location

        print("  ... done")

      print("opening " + file_path_to_load)
      with open(file_path_to_load, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        print("creating event footprint values")
        values_to_create = list()
        i = 0
        for row in reader:
          longitude = float(row.pop("Longitude"))
          latitude = float(row.pop("Latitude"))

          for key, val in row.items():
            if val == "-1":
              continue

            if sparse:
              if key not in events:
                continue

            values_to_create.append(
              HrscValueCoordinateWinterstorm(
                event=events[key],
                value=val,
                location=location_dict[(longitude, latitude)],
              )
            )

          i += 1
          if i > 5000:
            print(" bulk creating")
            HrscValueCoordinateWinterstorm.objects.bulk_create(values_to_create)
            values_to_create = list()
            i = 0
            print("   ... done")

        print("  ... done")

        print(" bulk creating (rest)")
        HrscValueCoordinateWinterstorm.objects.bulk_create(values_to_create)
        print("  ... done")
