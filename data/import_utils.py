import re

import fiona
from data.data_region.country_list import (
  get_country_dict_by_2alpha,
  get_nuts_by_code,
  get_nuts_translation,
)
from data.models import DataTableMetadata, Nuts3Area

country_dict = get_country_dict_by_2alpha()
nuts_dict = get_nuts_by_code()
nuts_translation = get_nuts_translation()


def initialize_nuts3_regions(filename, content, connection):
  regexp_str = "^[a-zA-Z_\-][0-9a-zA-Z_\-]*$"
  table_name_check = re.compile(regexp_str)

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

  geometry_bbox = dict()
  print("loading bbox geometry")
  cur_geometry = connection.cursor()
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

  return geometry_shapes, table_name
