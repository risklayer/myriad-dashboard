from typing import Tuple

from django.db import models


class Country(models.Model):
  country_code = models.TextField(unique=True)
  label = models.TextField()

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


# class VulnerabilityCurve():
#  param_asdf1
#  param_asdf2
