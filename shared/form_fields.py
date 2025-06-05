from itertools import groupby
from django.forms import (
  ModelChoiceField,
  ModelMultipleChoiceField,
)

from django.forms.models import (
  ModelChoiceIterator,
)

from data.models import Hazard
from shared.utils import rgetattr


class GroupedModelChoiceIterator(ModelChoiceIterator):
  def __init__(self, field, *args, group_by: str, **kwargs):
    super(GroupedModelChoiceIterator, self).__init__(field, *args, **kwargs)
    self.group_by = group_by

  def __iter__(self):
    if self.field.empty_label is not None:
      yield ("", self.field.empty_label)
    queryset = self.field.queryset
    # Can't use iterator() when queryset uses prefetch_related()
    if not queryset._prefetch_related_lookups:
      queryset = queryset.iterator()

    groups = groupby(queryset, key=lambda x: rgetattr(x, self.group_by, None))
    for group, values in groups:
      yield (group, [self.choice(value) for value in values])


class LabelSelectionField(ModelChoiceField):
  def __init__(
    self, *args, title_case=False, sentence_case=False, group_by: str | None = None, **kwargs
  ):
    super(LabelSelectionField, self).__init__(*args, **kwargs)
    self.title_case = title_case
    self.sentence_case = sentence_case
    if group_by:
      self.iterator = lambda s: GroupedModelChoiceIterator(s, group_by=group_by)

  def label_from_instance(self, obj):
    if self.title_case:
      return obj.label.replace("_", " ").title()
    if self.sentence_case:
      return obj.label.replace("_", " ").capitalize()
    return obj.label


class LabelSelectionFieldWithHazardUnits(LabelSelectionField):
  hazard: Hazard = None

  def label_from_instance(self, obj):
    # TODO allow access without to_dict?
    hazard_dict = self.hazard.to_dict() if self.hazard else dict()
    unit = hazard_dict.get("unit")

    label = super().label_from_instance(obj)

    return f"{label} {unit}" if unit else label


class LabelSelectionMultipleField(ModelMultipleChoiceField):
  def __init__(self, *args, title_case=False, sentence_case=False, **kwargs):
    super(LabelSelectionMultipleField, self).__init__(*args, **kwargs)
    self.title_case = title_case
    self.sentence_case = sentence_case

  def label_from_instance(self, obj):
    if self.title_case:
      return obj.label.replace("_", " ").title()
    if self.sentence_case:
      return obj.label.replace("_", " ").capitalize()
    return obj.label


# class DescriptionSelectionMultipleField(ModelMultipleChoiceField):
#   def label_from_instance(self, obj):
#     return obj.description


# From https://colorbrewer2.org/, selected via chroma.js
brewer_colors = {
  # diverging
  "RdYlGn": [
    "#a50026",
    "#d73027",
    "#f46d43",
    "#fdae61",
    "#fee08b",
    "#ffffbf",
    "#d9ef8b",
    "#a6d96a",
    "#66bd63",
    "#1a9850",
    "#006837",
  ],
  "Spectral": [
    "#9e0142",
    "#d53e4f",
    "#f46d43",
    "#fdae61",
    "#fee08b",
    "#ffffbf",
    "#e6f598",
    "#abdda4",
    "#66c2a5",
    "#3288bd",
    "#5e4fa2",
  ],
  "RdBu": [
    "#67001f",
    "#b2182b",
    "#d6604d",
    "#f4a582",
    "#fddbc7",
    "#f7f7f7",
    "#d1e5f0",
    "#92c5de",
    "#4393c3",
    "#2166ac",
    "#053061",
  ],
  "PiYG": [
    "#8e0152",
    "#c51b7d",
    "#de77ae",
    "#f1b6da",
    "#fde0ef",
    "#f7f7f7",
    "#e6f5d0",
    "#b8e186",
    "#7fbc41",
    "#4d9221",
    "#276419",
  ],
  "PRGn": [
    "#40004b",
    "#762a83",
    "#9970ab",
    "#c2a5cf",
    "#e7d4e8",
    "#f7f7f7",
    "#d9f0d3",
    "#a6dba0",
    "#5aae61",
    "#1b7837",
    "#00441b",
  ],
  "RdYlBu": [
    "#a50026",
    "#d73027",
    "#f46d43",
    "#fdae61",
    "#fee090",
    "#ffffbf",
    "#e0f3f8",
    "#abd9e9",
    "#74add1",
    "#4575b4",
    "#313695",
  ],
  "BrBG": [
    "#543005",
    "#8c510a",
    "#bf812d",
    "#dfc27d",
    "#f6e8c3",
    "#f5f5f5",
    "#c7eae5",
    "#80cdc1",
    "#35978f",
    "#01665e",
    "#003c30",
  ],
  "RdGy": [
    "#67001f",
    "#b2182b",
    "#d6604d",
    "#f4a582",
    "#fddbc7",
    "#ffffff",
    "#e0e0e0",
    "#bababa",
    "#878787",
    "#4d4d4d",
    "#1a1a1a",
  ],
  "PuOr": [
    "#7f3b08",
    "#b35806",
    "#e08214",
    "#fdb863",
    "#fee0b6",
    "#f7f7f7",
    "#d8daeb",
    "#b2abd2",
    "#8073ac",
    "#542788",
    "#2d004b",
  ],
  # sequential
  "OrRd": [
    "#7f0000",
    "#b30000",
    "#d7301f",
    "#ef6548",
    "#fc8d59",
    "#fdbb84",
    "#fdd49e",
    "#fee8c8",
    "#fff7ec",
  ],
  "PuBu": [
    "#023858",
    "#045a8d",
    "#0570b0",
    "#3690c0",
    "#74a9cf",
    "#a6bddb",
    "#d0d1e6",
    "#ece7f2",
    "#fff7fb",
  ],
  "BuPu": [
    "#4d004b",
    "#810f7c",
    "#88419d",
    "#8c6bb1",
    "#8c96c6",
    "#9ebcda",
    "#bfd3e6",
    "#e0ecf4",
    "#f7fcfd",
  ],
  "Oranges": [
    "#7f2704",
    "#a63603",
    "#d94801",
    "#f16913",
    "#fd8d3c",
    "#fdae6b",
    "#fdd0a2",
    "#fee6ce",
    "#fff5eb",
  ],
  "BuGn": [
    "#00441b",
    "#006d2c",
    "#238b45",
    "#41ae76",
    "#66c2a4",
    "#99d8c9",
    "#ccece6",
    "#e5f5f9",
    "#f7fcfd",
  ],
  "YlOrBr": [
    "#662506",
    "#993404",
    "#cc4c02",
    "#ec7014",
    "#fe9929",
    "#fec44f",
    "#fee391",
    "#fff7bc",
    "#ffffe5",
  ],
  "YlGn": [
    "#004529",
    "#006837",
    "#238443",
    "#41ab5d",
    "#78c679",
    "#addd8e",
    "#d9f0a3",
    "#f7fcb9",
    "#ffffe5",
  ],
  "Reds": [
    "#67000d",
    "#a50f15",
    "#cb181d",
    "#ef3b2c",
    "#fb6a4a",
    "#fc9272",
    "#fcbba1",
    "#fee0d2",
    "#fff5f0",
  ],
  "RdPu": [
    "#49006a",
    "#7a0177",
    "#ae017e",
    "#dd3497",
    "#f768a1",
    "#fa9fb5",
    "#fcc5c0",
    "#fde0dd",
    "#fff7f3",
  ],
  "Greens": [
    "#00441b",
    "#006d2c",
    "#238b45",
    "#41ab5d",
    "#74c476",
    "#a1d99b",
    "#c7e9c0",
    "#e5f5e0",
    "#f7fcf5",
  ],
  "YlGnBu": [
    "#081d58",
    "#253494",
    "#225ea8",
    "#1d91c0",
    "#41b6c4",
    "#7fcdbb",
    "#c7e9b4",
    "#edf8b1",
    "#ffffd9",
  ],
  "Purples": [
    "#3f007d",
    "#54278f",
    "#6a51a3",
    "#807dba",
    "#9e9ac8",
    "#bcbddc",
    "#dadaeb",
    "#efedf5",
    "#fcfbfd",
  ],
  "GnBu": [
    "#084081",
    "#0868ac",
    "#2b8cbe",
    "#4eb3d3",
    "#7bccc4",
    "#a8ddb5",
    "#ccebc5",
    "#e0f3db",
    "#f7fcf0",
  ],
  "Greys": [
    "#000000",
    "#252525",
    "#525252",
    "#737373",
    "#969696",
    "#bdbdbd",
    "#d9d9d9",
    "#f0f0f0",
    "#ffffff",
  ],
  "YlOrRd": [
    "#800026",
    "#bd0026",
    "#e31a1c",
    "#fc4e2a",
    "#fd8d3c",
    "#feb24c",
    "#fed976",
    "#ffeda0",
    "#ffffcc",
  ],
  "PuRd": [
    "#67001f",
    "#980043",
    "#ce1256",
    "#e7298a",
    "#df65b0",
    "#c994c7",
    "#d4b9da",
    "#e7e1ef",
    "#f7f4f9",
  ],
  "Blues": [
    "#08306b",
    "#08519c",
    "#2171b5",
    "#4292c6",
    "#6baed6",
    "#9ecae1",
    "#c6dbef",
    "#deebf7",
    "#f7fbff",
  ],
  "PuBuGn": [
    "#014636",
    "#016c59",
    "#02818a",
    "#3690c0",
    "#67a9cf",
    "#a6bddb",
    "#d0d1e6",
    "#ece2f0",
    "#fff7fb",
  ],
  "Viridis": [
    "#fee825",
    "#b6de2b",
    "#6cce5a",
    "#1f9d8a",
    "#26838f",
    "#31678e",
    "#3f4a8a",
    "#482777",
    "#440154",
  ],
  # qualitative
  # "Set2": ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3"],
  # "Accent": [
  #   "#7fc97f",
  #   "#beaed4",
  #   "#fdc086",
  #   "#ffff99",
  #   "#386cb0",
  #   "#f0027f",
  #   "#bf5b17",
  #   "#666666",
  # ],
  # "Set1": [
  #   "#e41a1c",
  #   "#377eb8",
  #   "#4daf4a",
  #   "#984ea3",
  #   "#ff7f00",
  #   "#ffff33",
  #   "#a65628",
  #   "#f781bf",
  #   "#999999",
  # ],
  # "Set3": [
  #   "#8dd3c7",
  #   "#ffffb3",
  #   "#bebada",
  #   "#fb8072",
  #   "#80b1d3",
  #   "#fdb462",
  #   "#b3de69",
  #   "#fccde5",
  #   "#d9d9d9",
  #   "#bc80bd",
  #   "#ccebc5",
  #   "#ffed6f",
  # ],
  # "Dark2": ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d", "#666666"],
  # "Paired": [
  #   "#a6cee3",
  #   "#1f78b4",
  #   "#b2df8a",
  #   "#33a02c",
  #   "#fb9a99",
  #   "#e31a1c",
  #   "#fdbf6f",
  #   "#ff7f00",
  #   "#cab2d6",
  #   "#6a3d9a",
  #   "#ffff99",
  #   "#b15928",
  # ],
  # "Pastel2": [
  #   "#b3e2cd",
  #   "#fdcdac",
  #   "#cbd5e8",
  #   "#f4cae4",
  #   "#e6f5c9",
  #   "#fff2ae",
  #   "#f1e2cc",
  #   "#cccccc",
  # ],
  # "Pastel1": [
  #   "#fbb4ae",
  #   "#b3cde3",
  #   "#ccebc5",
  #   "#decbe4",
  #   "#fed9a6",
  #   "#ffffcc",
  #   "#e5d8bd",
  #   "#fddaec",
  #   "#f2f2f2",
  # ],
}

brewer_colors_list = [(k, brewer_colors[k]) for k in brewer_colors.keys()]
