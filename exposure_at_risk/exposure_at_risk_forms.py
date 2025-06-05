import math
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
  Layout,
)
from django.db.models import Max, Min, Q
from django.forms import (
  ChoiceField,
  FloatField,
  Form,
  ModelChoiceField,
  SelectMultiple,
)

from data.models import (
  DataTableColumn,
  DataTableColumnMetadata,
  DataTableColumnMetadataValueString,
  Hazard,
  TableMetaExposure,
  TableMetaReturnPeriod,
  TableMetaThreshold,
)
from shared.form_fields import (
  LabelSelectionField,
  LabelSelectionFieldWithHazardUnits,
  LabelSelectionMultipleField,
)
from shared.utils import make_choices


class ExposureAtRiskFilterForm(Form):
  hazard = LabelSelectionField(
    queryset=Hazard.objects.exclude(key="EQ_flood")
    .filter(datatablecolumn__in=DataTableColumn.objects.all())
    .distinct()
    .order_by("label"),
    empty_label="",
    to_field_name="key",
    required=False,
    blank=False,
    # initial=0,
  )
  return_period = LabelSelectionField(
    queryset=TableMetaReturnPeriod.objects.all().order_by("key"),
    empty_label="",
    to_field_name="key",
    required=False,
    # initial=0,
  )
  threshold = LabelSelectionFieldWithHazardUnits(
    queryset=TableMetaThreshold.objects.all().order_by("key"),
    empty_label="",
    to_field_name="key",
    required=False,
    initial=0,
    title_case=True,
  )
  exposure = LabelSelectionField(
    sentence_case=True,
    queryset=TableMetaExposure.objects.all()
    .select_related("group")
    .order_by("group__label", "label"),
    empty_label="",
    to_field_name="key",
    required=False,
    initial=0,
    group_by="group.label",
  )
  # We don't use multiple but use it as a hack so it has no blank options
  column = LabelSelectionMultipleField(
    sentence_case=True,
    queryset=DataTableColumn.objects.all()
    .exclude(datatablecolumnmetadatavaluestring__metadata__key__in=("nace_code", "category"))
    .order_by("key"),
    to_field_name="key",
    required=False,
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
    super(ExposureAtRiskFilterForm, self).__init__(*args, **kwargs)

    meta_field_names = self.configure_fields()

    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.disable_csrf = True
    self.helper.label_class = "col-12"
    self.helper.field_class = "col-12 pb-0"
    self.helper.layout = Layout(
      "hazard",
      *meta_field_names,
    )

  def configure_fields(self):
    self.full_clean()

    has_data = hasattr(self, "cleaned_data")

    if not has_data:
      self.fields["column"].queryset = DataTableColumn.objects.none()
      return list()

    # if not has_data
    hazard = self.cleaned_data.get("hazard")

    # Allow threshold field to use units from selected hazard
    self.fields["threshold"].hazard = hazard

    self.fields["column"].queryset = self.fields["column"].queryset.filter(hazard=hazard)

    children = ["exposure", "return_period", "threshold"]

    filter_meta_fields = DataTableColumnMetadata.objects.none()

    if hazard:
      filter_meta_fields = (
        DataTableColumnMetadata.objects
        # .exclude(key__in=non_filter_keys)
        .filter(
          Q(datatablecolumnmetadatavaluefloat__column__hazard=hazard)
          | Q(datatablecolumnmetadatavaluestring__column__hazard=hazard)
        )
        .exclude(datatablecolumnmetadatavaluestring__metadata__key__in=("nace_code", "category"))
        .distinct()
        .annotate(
          min=Min("datatablecolumnmetadatavaluefloat__value"),
          max=Max("datatablecolumnmetadatavaluefloat__value"),
        )
        .prefetch_related("datatablecolumnmetadatavaluestring_set")
        .order_by("label")
      )

    meta_field_names = list()
    meta_field_names_with_meta = list()
    for meta in filter_meta_fields:
      # TODO string fields
      label = getattr(meta, "label").replace("_", " ")
      key = getattr(meta, "key")

      if meta.type == "string":
        field_name = "metadata_s_%s" % (key)
        self.fields[field_name] = ChoiceField(
          label=label,
          required=False,
          choices=make_choices(
            DataTableColumnMetadataValueString.objects.filter(metadata=meta)
            .values_list("value", flat=True)
            .distinct()
            .order_by("value")
          ),
        )

        meta_field_names_with_meta.append((field_name, key, meta))
        meta_field_names.append(field_name)
      else:
        # float
        label = getattr(meta, "label").replace("_", " ")
        key = getattr(meta, "key")
        meta_min_val = getattr(meta, "min", None)
        meta_max_val = getattr(meta, "max", None)
        min_value = math.floor(meta_min_val) if meta_min_val is not None else None
        max_value = math.ceil(meta_max_val) if meta_max_val is not None else None
        field_name = "metadata_f_%s__min" % (key)
        [min_required, max_required] = getattr(meta, "required", (False, False))
        [min_initial, max_initial] = getattr(meta, "initial", (None, None))

        # if (
        #   min_required
        #   and min_initial is not None
        #   and (self.data.get(field_name) is None or self.data.get(field_name) == "")
        # ):
        #   overrides[field_name] = min_initial

        range = f"({min_value}–{max_value})"
        self.fields[field_name] = FloatField(
          required=min_required,
          label=f"Min. {label} {range}",
          min_value=min_value,
          max_value=max_value,
          initial=min_initial,
        )
        meta_field_names_with_meta.append((field_name, key, meta))
        meta_field_names.append(field_name)
        field_name = "metadata_f_%s__max" % (key)
        self.fields[field_name] = FloatField(
          required=max_required,
          label=f"Max. {label} {range}",
          min_value=min_value,
          max_value=max_value,
          initial=max_initial,
        )
        meta_field_names_with_meta.append((field_name, key, meta))
        meta_field_names.append(field_name)

    metadata_filters = list()

    # Populate the meta fields
    self.full_clean()
    for field_name, key, meta in meta_field_names_with_meta:
      value = self.cleaned_data.get(field_name, None)
      if value is not None and value != "":
        value_key = (
          field_name.replace(key, "")
          .replace("metadata_s_", "datatablecolumnmetadatavaluestring__value")
          .replace("metadata_f_", "datatablecolumnmetadatavaluefloat__value")
          .replace("__max", "__lte")
          .replace("__min", "__gte")
        )
        query = Q(
          **{value_key: value, f"datatablecolumnmetadatavalue{meta.type}__metadata_id": meta.id}
        )
        metadata_filters.append(query)

    # Filter other main columns by each other

    column_filter = {}

    for child in children:
      if hazard:
        self.fields[child].queryset = (
          self.fields[child].queryset.filter(datatablecolumn__hazard=hazard).distinct()
        )

      val = self.cleaned_data.get(child)

      count = self.fields[child].queryset.count()
      if count == 0 or not hazard:
        self.fields[child].widget = self.fields[child].hidden_widget()
      elif count > 0:
        meta_field_names.append(child)
        if val is not None and val.id in self.fields[child].queryset.values_list("id", flat=True):
          column_filter[child] = val
        else:
          self.cleaned_data[child] = None

    if len(column_filter.keys()):
      self.fields["column"].queryset = self.fields["column"].queryset.filter(**column_filter)

    for query in metadata_filters:
      self.fields["column"].queryset = self.fields["column"].queryset.filter(query)

    if self.fields["column"].queryset.count() == 1:
      self.cleaned_data["column"] = self.fields["column"].queryset[0:1]

    return meta_field_names
