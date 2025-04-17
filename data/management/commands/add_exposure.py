import os
import shutil
import sqlite3
import zipfile

from data.data_region.country_list import (
  get_country_dict_by_2alpha,
  get_nuts_by_code,
  get_nuts_translation,
)
from data.import_utils import initialize_nuts3_regions
from data.models import HrscExposure, HrscExposureColumnValue, HrscExposureRaster
from django.conf import settings
from django.core.management.base import BaseCommand

country_dict = get_country_dict_by_2alpha()
nuts_dict = get_nuts_by_code()
nuts_translation = get_nuts_translation()


class Command(BaseCommand):
  help = "Add a data set"

  def add_arguments(self, parser):
    parser.add_argument("--key", type=str, required=True)
    parser.add_argument("--label", type=str, required=True)

    parser.add_argument("--raster-filename", dest="raster_filename", type=str)
    parser.add_argument("--raster-zip-filename", dest="raster_zip_filename", type=str)
    parser.add_argument("--raster-cell-size", dest="raster_cell_size", type=float)
    parser.add_argument("--raster-format", dest="raster_format", type=str, choices=["tiff"])

    parser.add_argument("--nuts3-filename", dest="nuts3_filename", type=str)
    parser.add_argument("--nuts3-format", dest="nuts3_format", type=str, choices=["gpkg-sqlite"])
    parser.add_argument("--nuts3-gpkg-identifier", dest="nuts3_gpkg_identifier", type=str)

  def handle(
    self,
    *args,
    key: str,
    label: str,
    raster_filename: str = None,
    raster_zip_filename: str = None,
    raster_cell_size: str = None,
    raster_format: str = None,
    nuts3_filename: str = None,
    nuts3_format: str = None,
    nuts3_gpkg_identifier: str = None,
    **options,
  ):
    exposure = HrscExposure.get_or_create_by_label(label=label, slug_key=key)

    if nuts3_filename:
      if nuts3_format == "gpkg-sqlite":
        all_values = list()
        with sqlite3.connect(nuts3_filename) as con:
          con.row_factory = sqlite3.Row

          cur_tables = con.cursor()
          res_tables = cur_tables.execute(
            "SELECT table_name, data_type, identifier, description, last_change, min_x, min_y, max_x, max_y, srs_id FROM gpkg_contents"
          )
          for content in res_tables.fetchall():
            geometry_shapes, table_name = initialize_nuts3_regions(
              filename=nuts3_filename, content=content, connection=con
            )

            cur_columns = con.cursor()
            res_columns = cur_columns.execute('SELECT * FROM "' + table_name + '" WHERE True')
            column_keys = set([d[0] for d in cur_columns.description])
            column_keys = column_keys.difference({"fid", "geom", "NUTS_ID", "CNTR_CODE"})

            HrscExposureColumnValue.objects.filter(exposure=exposure).delete()

            for row in res_columns.fetchall():
              data_value = row[nuts3_gpkg_identifier]

              # if data_value is None:
              #  continue

              all_values.append(
                HrscExposureColumnValue(
                  exposure=exposure,
                  nuts3area=geometry_shapes[row["NUTS_ID"]],
                  value=data_value,
                )
              )

        HrscExposureColumnValue.objects.bulk_create(all_values)

      else:
        raise Exception("unknown nuts3 data format")

    if raster_filename:
      # remove old one
      HrscExposureRaster.objects.filter(exposure=exposure).delete()

      subpath = os.path.join("hrsc", "exposure", key + os.path.splitext(raster_filename)[1])
      output_file_path = os.path.join(settings.RASTER_DATA_ROOT, subpath)

      os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

      if raster_zip_filename:
        with zipfile.ZipFile(raster_zip_filename, "r") as zip_ref:
          with zip_ref.open(raster_filename) as source_file:
            with open(output_file_path, "wb") as output_file:
              output_file.write(source_file.read())
      else:
        shutil.copyfile(raster_filename, output_file_path)

      HrscExposureRaster.objects.create(
        exposure=exposure,
        cell_size=raster_cell_size,
        file=subpath,
        file_type=raster_format,
      )
