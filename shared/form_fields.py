from django.forms import (
  ModelChoiceField,
  ModelMultipleChoiceField,
)

from data.models import Hazard


class LabelSelectionField(ModelChoiceField):
  def label_from_instance(self, obj):
    return obj.label


class LabelSelectionFieldWithHazardUnits(ModelChoiceField):
  hazard: Hazard = None

  def label_from_instance(self, obj):
    # TODO allow access without to_dict?
    hazard_dict = self.hazard.to_dict()
    unit = hazard_dict.get("unit")

    return f"{obj.label} {unit}" if unit else obj.label


class LabelSelectionMultipleField(ModelMultipleChoiceField):
  def label_from_instance(self, obj):
    return obj.label


# class DescriptionSelectionMultipleField(ModelMultipleChoiceField):
#   def label_from_instance(self, obj):
#     return obj.description


# From https://colorbrewer2.org/, selected via chroma.js
brewer_colors = [
  # Diverging
  "RdYlGn",
  "RdBu",
  "PiYG",
  "PRGn",
  "RdYlBu",
  "BrBG",
  "RdGy",
  "PuOr",
  "Spectral",
  # Sequential
  "OrRd",
  "PuBu",
  "BuPu",
  "Oranges",
  "BuGn",
  "YlOrBr",
  "YlGn",
  "Reds",
  "RdPu",
  "Greens",
  "YlGnBu",
  "Purples",
  "GnBu",
  "Greys",
  "YlOrRd",
  "PuRd",
  "Blues",
  "PuBuGn",
]
