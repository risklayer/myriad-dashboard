import sqlite3

from data.models import (
  DataTableColumn,
  DataTableColumnValue,
  DataTableMetadata,
  Nuts3Area,
  Hazard,
  TableMetaExposure,
  TableMetaThreshold,
  TableMetaReturnPeriod,
  TableHazardUnit,
  DataTableColumnMetadata,
  DataTableColumnMetadataValueString,
  DataTableColumnMetadataValueFloat,
)
from django.core.management.base import BaseCommand
from data.data_region.country_list import (
  get_country_dict_by_2alpha,
  get_nuts_by_code,
  get_nuts_translation,
)
import re

import fiona

import json

from django.db import models
from typing import Type, Dict


country_dict = get_country_dict_by_2alpha()
nuts_dict = get_nuts_by_code()
nuts_translation = get_nuts_translation()


class Command(BaseCommand):
  help = "Add a data set"

  def add_arguments(self, parser):
    parser.add_argument("--filename", type=str, required=True)
    parser.add_argument("--format", type=str, required=True, choices=["gpkg-sqlite", "xlsx"])
    parser.add_argument("--table-metadata", type=str, required=True, dest="table_metadata")
    parser.add_argument("--skip-existing", action="store_true", default=False, dest="skip_existing")

  def handle(
    self, *args, filename: str, format: str, table_metadata: str, skip_existing: bool, **options
  ):
    table_metadata = json.load(open(table_metadata))

    def ensureTableMetaParameterCreation(
      cls: Type[models.Model], data: dict, cls_dict=Dict[str, models.Model]
    ):
      for key, data in data["values"].items():
        if isinstance(data, dict):
          unit = None
          if cls == Hazard:
            unit = data.pop("unit", None)
            instance_cls = cls.get_or_create_by_label(label=data["label"], slug_key=key)
          else:
            instance_cls = cls.get_or_create_by_label(
              label=data["label"], slug_key=key, unit=data.get("unit", None)
            )
          cls_dict[key] = instance_cls
          if unit:
            TableHazardUnit.objects.get_or_create(hazard=instance_cls, unit=unit)
        else:
          instance_cls = cls.get_or_create_by_label(label=data, slug_key=key)
          cls_dict[key] = instance_cls

    meta_dict_hazard = dict()
    ensureTableMetaParameterCreation(Hazard, table_metadata["hazard"], meta_dict_hazard)
    meta_dict_exposure = dict()
    ensureTableMetaParameterCreation(
      TableMetaExposure, table_metadata["exposure"], meta_dict_exposure
    )
    meta_dict_threshold = dict()
    ensureTableMetaParameterCreation(
      TableMetaThreshold, table_metadata["parameters"]["threshold"], meta_dict_threshold
    )
    meta_dict_return_period = dict()
    ensureTableMetaParameterCreation(
      TableMetaReturnPeriod, table_metadata["parameters"]["return_period"], meta_dict_return_period
    )

    column_metadata_dict = dict()
    if "additonal_metadata" in table_metadata["parameters"]:
      for key, metadata_info in table_metadata["parameters"]["additonal_metadata"].items():
        metadata_type = "float"
        for value_key, value_value in table_metadata["parameters"]["additonal_metadata"][key][
          "values"
        ].items():
          if not value_value.lstrip("-").replace(".", "").isdigit():
            metadata_type = "string"
            break

        meta = DataTableColumnMetadata.get_or_create_by_label(
          slug_key=key,
          label=metadata_info["label"],
          unit=metadata_info.get("unit", None),
          type=metadata_type,
          enable_histogram=(metadata_type == "float"),
        )

        column_metadata_dict[key] = meta

    regexp_str = "^[a-zA-Z_\-][0-9a-zA-Z_\-]*$"
    table_name_check = re.compile(regexp_str)
    if format == "gpkg-sqlite":
      all_values = list()
      with sqlite3.connect(filename) as con:
        con.row_factory = sqlite3.Row

        cur_tables = con.cursor()
        res_tables = cur_tables.execute(
          "SELECT table_name, data_type, identifier, description, last_change, min_x, min_y, max_x, max_y, srs_id FROM gpkg_contents"
        )
        for content in res_tables.fetchall():
          (
            table_name,
            data_type,
            identifier,
            description,
            last_change,
            min_x,
            min_y,
            max_x,
            max_y,
            srs_id,
          ) = content

          if not table_name_check.match(table_name):
            raise Exception(
              'table_name "'
              + table_name
              + '" forbidden to be used. Please change the name of the dataset to match '
              + regexp_str
            )

          geometry_bbox = dict()
          print("loading bbox geometry")
          cur_geometry = con.cursor()
          res_geometry = cur_geometry.execute(
            'SELECT NUTS_ID, minx, miny, maxx, maxy FROM "rtree_'
            + table_name
            + '_geom" INNER JOIN "'
            + table_name
            + '" on "rtree_'
            + table_name
            + '_geom".id = "'
            + table_name
            + '".fid'
          )
          for row in res_geometry.fetchall():
            geometry_bbox[row["NUTS_ID"]] = (
              row["minx"],
              row["miny"],
              row["maxx"],
              row["maxy"],
            )

          geometry_shapes = dict()
          print("loading shape geometry")
          with fiona.open(filename, layer=table_name) as data_collection:
            for feature in data_collection:
              nuts_id = feature.properties["NUTS_ID"]
              label = nuts_id
              code_2alpha = nuts_id[0:2]
              country_label = nuts_id[0:2]

              if code_2alpha == "UK":
                code_2alpha = "GB"

              if nuts_id in nuts_dict:
                nuts_data = nuts_dict[nuts_id]

                code_2alpha = nuts_data["code_2alpha"]
                label = nuts_data["label"]
                if nuts_data["code_nuts"] in nuts_translation:
                  label = nuts_translation[nuts_data["code_nuts"]]["label_latin"]

              if code_2alpha in country_dict:
                country_label = country_dict[code_2alpha]["name_short"]

              geometry_shapes[nuts_id] = Nuts3Area.ensure_creation(
                nuts_id,
                code_2alpha,
                label,
                country_label,
                geometry_bbox[nuts_id],
                geom_json={
                  "type": feature.geometry.type,
                  "coordinates": feature.geometry.coordinates,
                },
              )

          metadata, created = DataTableMetadata.objects.get_or_create(key=identifier)
          metadata.source_metadata = {
            "table_name": table_name,
            "data_type": data_type,
            "identifier": identifier,
            "description": description,
            "last_change": last_change,
            "min_x": min_x,
            "min_y": min_y,
            "max_x": max_x,
            "max_y": max_y,
            "srs_id": srs_id,
          }
          metadata.save()

          cur_columns = con.cursor()
          res_columns = cur_columns.execute('SELECT * FROM "' + table_name + '" WHERE True')
          column_keys = set([d[0] for d in cur_columns.description])
          column_keys = column_keys.difference({"fid", "geom", "NUTS_ID", "CNTR_CODE"})

          columns = list()
          columns_dict = dict()

          for column_key in column_keys:
            if column_key not in table_metadata["columns"]:
              print("skipping " + column_key + " (no metadata)")
              continue
            column_metadata = table_metadata["columns"][column_key]

            threshold = None
            if "threshold" in column_metadata:
              threshold = meta_dict_threshold[column_metadata["threshold"]]

            return_period = None
            if "return_period" in column_metadata:
              return_period = meta_dict_return_period[column_metadata["return_period"]]

            exposure = None
            if "exposure" in column_metadata:
              exposure = meta_dict_exposure[column_metadata["exposure"]]

            column, created = DataTableColumn.objects.get_or_create(
              data_table=metadata,
              key=column_key,
              defaults={
                "label": column_key,
                "description": column_metadata["description"],
                "hazard": meta_dict_hazard[column_metadata["hazard"]],
                "exposure": exposure,
                "threshold": threshold,
                "return_period": return_period,
              },
            )
            if not created:
              print("removing column " + str(column))
              DataTableColumnValue.objects.filter(data_table_column=column).delete()

            for metadata_key in column_metadata_dict.keys() & column_metadata.keys():
              metadata_inst = column_metadata_dict[metadata_key]
              if metadata_inst.type == "string":
                DataTableColumnMetadataValueString.objects.get_or_create(
                  metadata=metadata_inst,
                  column=column,
                  defaults={
                    "value": table_metadata["parameters"]["additonal_metadata"][metadata_key][
                      "values"
                    ][column_metadata[metadata_key]]
                  },
                )
              elif metadata_inst.type == "float":
                DataTableColumnMetadataValueFloat.objects.get_or_create(
                  metadata=metadata_inst,
                  column=column,
                  defaults={
                    "value": table_metadata["parameters"]["additonal_metadata"][metadata_key][
                      "values"
                    ][column_metadata[metadata_key]]
                  },
                )

            if skip_existing and not created:
              print("skipping " + column_key + " (already existing)")
            else:
              columns.append(column)
              columns_dict[column.key] = column

          for row in res_columns.fetchall():
            for column in columns:
              data_value = row[column.key]

              if data_value is None:
                continue

              all_values.append(
                DataTableColumnValue(
                  data_table_column=column,
                  nuts_area=geometry_shapes[row["NUTS_ID"]],
                  value=data_value,
                )
              )

      DataTableColumnValue.objects.bulk_create(all_values)

    elif format == "xlsx":
      pass
    else:
      print("unknown format")
