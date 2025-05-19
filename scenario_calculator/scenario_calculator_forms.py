import math

from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from django.db.models import Max, Min
from django.forms import (
  FloatField,
  Form,
  HiddenInput,
  IntegerField,
  ModelMultipleChoiceField,
  Select,
  SelectMultiple,
)
from django.forms.fields import (
  ChoiceField,
)

from data.models import (
  Hazard,
  HrscEvent,
  HrscEventCollection,
  HrscEventMetadata,
  HrscExposure,
  HrscHazardProbabilityRaster,
  HrscHazardProbabilityRasterInstance,
)
from data.v1.hrsc import get_events_by_collection_filter, get_events_by_collection_filter_ws
from scenario_calculator.config import (
  DEFAULT_LATITUDE,
  DEFAULT_LONGITUDE,
  DEFAULT_RADIUS,
)
from shared.form_fields import (
  LabelSelectionField,
)
from shared.utils import make_choices

from .config import non_filter_keys

# class RangeInput(NumberInput):
#   input_type = "range"


TIME_UNITS = ["days", "months", "years"]


class ScenarioCalculatorProbabilitySharedForm(Form):
  latitude = FloatField(
    required=True,
    initial=DEFAULT_LATITUDE,
    min_value=-90,
    max_value=90,
  )
  longitude = FloatField(
    required=True,
    initial=DEFAULT_LONGITUDE,
    min_value=-180,
    max_value=180,
  )
  time_window = IntegerField(
    required=True,
    initial=1,
    min_value=0,
  )
  time_window_unit = ChoiceField(
    required=True,
    initial=("days", "Days"),
    label="Unit",
    choices=make_choices(TIME_UNITS, include_blank=False, sort=False),
  )


class ScenarioCalculatorProbabilityForm(Form):
  hazard = LabelSelectionField(
    sentence_case=True,
    queryset=Hazard.objects.filter(
      id__in=HrscHazardProbabilityRaster.objects.all()
      .distinct()
      .select_related("hazard")
      .values_list("hazard", flat=True)
      .distinct()
    )
    .distinct()
    .order_by("label"),
    empty_label=None,
    to_field_name="key",
    required=False,
    blank=True,
  )

  severity = LabelSelectionField(
    queryset=HrscHazardProbabilityRasterInstance.objects.all().distinct(),
    # title_case=True,
    empty_label=None,
    to_field_name="id",
    required=False,
    blank=False,
  )

  def __init__(self, *args, **kwargs):
    super(ScenarioCalculatorProbabilityForm, self).__init__(*args, **kwargs)

    self.full_clean()

    hazard = None
    if hasattr(self, "cleaned_data"):
      hazard = self.cleaned_data.get("hazard")

    if hazard is None:
      hazard = self.fields["hazard"].queryset.first()

    self.fields["severity"].queryset = (
      (
        self.fields["severity"]
        .queryset.filter(probability_raster__hazard=hazard)
        .order_by("severity_value")
      )
      if hazard
      else self.fields["severity"].queryset.none()
    )

    # self.full_clean()

    # if hasattr(self, "cleaned_data"):
    #   severity = self.cleaned_data["severity"]

    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.disable_csrf = True
    self.helper.label_class = "col-12"
    self.helper.field_class = "col-12 pb-0"
    self.helper.layout = Layout(
      "hazard", "severity" if (hazard and self.fields["severity"].queryset.count()) else None
    )


class ScenarioCalculatorHazardFilterForm(Form):
  hazard = LabelSelectionField(
    sentence_case=True,
    queryset=Hazard.objects.filter(hrsceventcollection__in=HrscEventCollection.objects.all())
    .distinct()
    .order_by("label"),
    empty_label="Select a hazard",
    to_field_name="key",
    required=False,
    blank=True,
    # initial=0,
  )
  collection = LabelSelectionField(
    queryset=HrscEventCollection.objects.all().order_by("label"),
    empty_label=None,
    to_field_name="key",
    required=False,
    blank=False,
    # initial=0,
  )
  latitude = FloatField(
    required=False,
    initial=DEFAULT_LATITUDE,
    min_value=-90,
    max_value=90,
    widget=HiddenInput,
  )
  longitude = FloatField(
    required=False,
    initial=DEFAULT_LONGITUDE,
    min_value=-180,
    max_value=180,
    widget=HiddenInput,
  )
  radius = IntegerField(
    required=False,
    initial=DEFAULT_RADIUS,
    min_value=1,
    max_value=10000,
    widget=HiddenInput,
  )
  color_by = LabelSelectionField(
    sentence_case=True,
    empty_label=None,
    queryset=HrscEventMetadata.objects.none(),
    to_field_name="key",
    required=False,
    blank=False,
    widget=Select(
      {
        "onchange": "formUpdate(undefined, {zoomToFit: false})",
      }
    ),
  )
  # We don't use multiple but use it as a hack so it has no blank options
  event = ModelMultipleChoiceField(
    queryset=HrscEvent.objects.none(),
    to_field_name="id",
    required=False,
    blank=False,
    widget=SelectMultiple(
      {
        "onchange": "formUpdate()",
      }
    ),
  )

  def update_choices(self, possible_values: dict):
    for key, values in possible_values.items():
      if key in self.fields:
        self.fields[key].choices = make_choices(values)

  def __init__(self, *args, **kwargs):
    super(ScenarioCalculatorHazardFilterForm, self).__init__(*args, **kwargs)

    only_one_collection, meta_field_names = self.configure_fields()

    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.disable_csrf = True
    self.helper.label_class = "col-12"
    self.helper.field_class = "col-12 pb-0"
    self.helper.layout = Layout(
      "hazard",
      None if only_one_collection else "collection",
      *meta_field_names,
      StrictButton(
        "Search here",
        id="id_search_here",
        css_class="btn btn-secondary w-100 mb-3",
        onclick="searchHere()",
        type="submit",
      ),
      "latitude",
      "longitude",
      "radius",
      # "return_period",
      # "threshold",
      # "exposure",
    )

  def configure_fields(self):
    self.full_clean()
    has_data = hasattr(self, "cleaned_data")
    if not has_data:
      # hazard = self.fields["hazard"].queryset.first()
      # self.initial["hazard"] = hazard.key
      # self.fields["collection"].queryset = self.fields["collection"].queryset.filter(hazard=hazard)
      self.fields["collection"].queryset = self.fields["collection"].queryset.none()
      # only_one_collection = self.fields["collection"].queryset.count() == 1
      only_one_collection = True
      # collection = self.fields["collection"].queryset.first()
      collection = None
      # self.initial["collection"] = collection.key
      longitude = DEFAULT_LONGITUDE
      latitude = DEFAULT_LATITUDE
      radius = DEFAULT_RADIUS
    else:
      hazard = self.cleaned_data.get("hazard")

      # if not hazard:
      #   hazard = self.cleaned_data["hazard"] = self.fields["hazard"].queryset.first()
      #   self.initial["hazard"] = hazard.key

      self.fields["collection"].queryset = self.fields["collection"].queryset.filter(hazard=hazard)

      only_one_collection = self.fields["collection"].queryset.count() <= 1

      collection = (
        self.fields["collection"].queryset.first()
        if only_one_collection
        else self.cleaned_data.get("collection")
      )

      if collection and collection.key != self.data.get("collection"):
        self.initial["collection"] = collection.key

      latitude = self.cleaned_data.get("latitude")
      if not latitude:
        latitude = self.data["latitude"] = self.cleaned_data["latitude"] = self.initial[
          "latitude"
        ] = DEFAULT_LATITUDE
      longitude = self.cleaned_data.get("longitude")
      if not longitude:
        longitude = self.data["longitude"] = self.cleaned_data["longitude"] = self.initial[
          "longitude"
        ] = DEFAULT_LONGITUDE
      radius = self.cleaned_data.get("radius")
      if not radius:
        radius = self.data["radius"] = self.cleaned_data["radius"] = self.initial["radius"] = (
          DEFAULT_RADIUS
        )

    # This section regardless of whether it's a fresh load or not
    filter_meta_fields = HrscEventMetadata.objects.none()

    if collection:
      if collection.key == "winterstorm":
        filter_meta_fields = [
          {
            "key": "value",
            "label": "Wind speed (km/h)",
            "required": (True, False),
            "initial": (100, None),
          }
        ]
      else:
        filter_meta_fields = (
          HrscEventMetadata.objects.exclude(key__in=non_filter_keys)
          .filter(
            hrsceventmetadatavaluefloat__event__collection=collection,
          )
          .distinct()
          .annotate(
            min=Min("hrsceventmetadatavaluefloat__value"),
            max=Max("hrsceventmetadatavaluefloat__value"),
          )
          .order_by("label")
        )

    # overrides = {}

    # Create fields for each meta float
    meta_field_names = list()
    for meta in filter_meta_fields:
      meta_dict = meta if isinstance(meta, dict) else meta.to_dict()
      label = meta_dict.get("label").replace("_", " ")
      key = meta_dict.get("key")
      meta_min_val = meta_dict.get("min", None)
      meta_max_val = meta_dict.get("max", None)
      min_value = math.floor(meta_min_val) if meta_min_val is not None else None
      max_value = math.ceil(meta_max_val) if meta_max_val is not None else None
      field_name = "metadata_%s__min" % (key)
      [min_required, max_required] = meta_dict.get("required", (False, False))
      [min_initial, max_initial] = meta_dict.get("initial", (None, None))

      # if (
      #   min_required
      #   and min_initial is not None
      #   and (self.data.get(field_name) is None or self.data.get(field_name) == "")
      # ):
      #   overrides[field_name] = min_initial

      self.fields[field_name] = FloatField(
        required=min_required,
        label="Minimum %s" % (label),
        min_value=min_value,
        max_value=max_value,
        initial=min_initial,
      )
      meta_field_names.append(field_name)
      field_name = "metadata_%s__max" % (key)
      self.fields[field_name] = FloatField(
        required=max_required,
        label="Maximum %s" % (label),
        min_value=min_value,
        max_value=max_value,
        initial=max_initial,
      )
      meta_field_names.append(field_name)

    if collection and getattr(collection, "key") != "winterstorm" and len(meta_field_names):
      self.fields["color_by"].queryset = filter_meta_fields
      meta_field_names.append("color_by")
      if not has_data:
        self.initial["color_by"] = meta_field_names[0]
      else:
        self.full_clean()
        color_by = self.cleaned_data["color_by"] = (
          self.cleaned_data.get("color_by") or filter_meta_fields.first()
        )

        self.initial["color_by"] = color_by.key

    metadata_filters = dict()

    if has_data:
      # Populate the meta fields
      self.full_clean()
      # for field in overrides:
      #   self.initial[field] = self.cleaned_data[field] = overrides[field]
      for field in meta_field_names:
        value = self.cleaned_data.get(field)
        if value is not None and value != "":
          metadata_filters[field] = value

    # for field in meta_field_names:
    #   value = self.cleaned_data.get(field) if has_data else overrides.get(field, None)
    #   if value is not None and value != "":
    #     filters[field] = value

    if self.errors:
      self.fields["event"].queryset = HrscEvent.objects.none()
    elif collection:
      if collection.key == "winterstorm":
        self.fields["event"].queryset = get_events_by_collection_filter_ws(
          longitude=longitude,
          latitude=latitude,
          radius=min(radius, 100),
          limit=100,
          value__min=metadata_filters.get("metadata_value__min", None),
          value__max=metadata_filters.get("metadata_value__max", None),
        )
      else:
        self.fields["event"].queryset = get_events_by_collection_filter(
          collection_key=collection.key,
          longitude=longitude,
          latitude=latitude,
          radius=radius,
          limit=100,
          filters=metadata_filters,
        )

    return only_one_collection, meta_field_names


color_choices = [
  ("impact_data_avrg_lin", "Impact average linear"),
  ("impact_data_avrg_sqrt", "Impact average square root"),
  ("impact_data_max", "Impact max"),
  ("impact_data_min", "Impact min"),
]


class ScenarioCalculatorCombineEventsForm(Form):
  exposure = LabelSelectionField(
    sentence_case=True,
    queryset=HrscExposure.objects.all().order_by("key"),
    empty_label="",
    to_field_name="key",
    required=False,
    initial=HrscExposure.objects.order_by("key").first().key,
  )

  color_results_by = ChoiceField(
    choices=color_choices,
    required=False,
    initial=("impact_data_avrg_lin", "Impact average linear"),
  )

  def __init__(self, *args, **kwargs):
    super(ScenarioCalculatorCombineEventsForm, self).__init__(*args, **kwargs)

    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.disable_csrf = True
    self.helper.label_class = "col-12"
    self.helper.field_class = "col-12 pb-0"
    self.helper.layout = Layout(
      "exposure",
      "color_results_by",
      StrictButton(
        "Calculate", css_class="btn btn-primary w-100 mb-3", onclick="calculateImpact()"
      ),
    )
