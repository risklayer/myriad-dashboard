from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
  Layout,
)
from django.forms import (
  CharField,
  Form,
  HiddenInput,
  Select,
  SelectMultiple,
)
from django.forms.fields import (
  ChoiceField,
)

from data.models import (
  Country,
  DataTableColumn,
  TableMetaExposure,
  Hazard,
  TableMetaReturnPeriod,
  TableMetaThreshold,
)
from shared.form_fields import (
  LabelSelectionField,
  LabelSelectionFieldWithHazardUnits,
  LabelSelectionMultipleField,
  brewer_colors,
)


def make_choices(items: set, include_blank=True, sort=True, blank: str = "Please select"):
  choices = [(x, x if x else blank) for x in (sorted(items) if sort else items)]
  return [(None, "")] + choices if include_blank else choices


class ExposureAtRiskSettingsForm(Form):
  colors = ChoiceField(
    required=False,
    choices=make_choices(
      brewer_colors,
      include_blank=False,
      sort=False,
    ),
    widget=Select(
      {
        "onchange": "formUpdate()",
      }
    ),
  )
  base_layer = CharField(widget=HiddenInput(), required=False)

  def __init__(self, *args, **kwargs):
    super(ExposureAtRiskSettingsForm, self).__init__(*args, **kwargs)
    self.full_clean()
    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.disable_csrf = True
    self.helper.label_class = "col-12"
    self.helper.field_class = "col-12 pb-0"


class ExposureAtRiskRegionsForm(Form):
  countries = LabelSelectionMultipleField(
    queryset=Country.objects.all().order_by("label"),
    to_field_name="country_code",
    required=False,
    widget=SelectMultiple(
      {
        "onchange": "formUpdate()",
      }
    ),
  )

  def create_countries_hierarchy(self):
    countries = Country.objects.order_by("label").prefetch_related("areas").order_by("label")

    selected_countries = set(self.data.getlist("countries"))
    selected_areas = set(self.data.getlist("areas"))
    all_selected = "ALL" in selected_countries
    # regions = Nuts2Area.objects.all().order_by("label")
    countries_tree = []
    for country in countries:
      areas = country.areas.all().order_by("label")
      if len(areas) == 0:
        continue
      selected = all_selected or country.country_code in selected_countries
      indeterminate = False
      if not selected and len(selected_areas):
        selected_areas_count = areas.filter(key__in=selected_areas).count()
        indeterminate = selected_areas_count > 0 and selected_areas_count < len(areas)
      countries_tree.append(
        {
          "type": "countries",
          "value": country.country_code,
          "label": country.label,
          "selected": selected,
          "indeterminate": indeterminate,
          "children": [
            {
              "type": "areas",
              "value": area.key,
              "label": area.label,
              "selected": selected or area.key in selected_areas,
            }
            for area in areas
          ],
        }
      )

    root = {
      "type": "countries",
      "value": "ALL",
      "label": "All",
      "selected": all_selected,
      "indeterminate": False,
      "children": countries_tree,
    }

    root["indeterminate"] = not root["selected"] and (
      any(c["indeterminate"] for c in countries_tree) or any(c["selected"] for c in countries_tree)
    )

    return root


class ExposureAtRiskFilterForm(Form):
  hazard = LabelSelectionField(
    queryset=Hazard.objects.all().order_by("label"),
    empty_label="",
    to_field_name="key",
    required=False,
    blank=False,
    initial=0,
  )
  return_period = LabelSelectionField(
    queryset=TableMetaReturnPeriod.objects.all().order_by("key"),
    empty_label="",
    to_field_name="key",
    required=False,
    initial=0,
  )
  threshold = LabelSelectionFieldWithHazardUnits(
    queryset=TableMetaThreshold.objects.all().order_by("key"),
    empty_label="",
    to_field_name="key",
    required=False,
    initial=0,
  )
  exposure = LabelSelectionField(
    queryset=TableMetaExposure.objects.all().order_by("key"),
    empty_label="",
    to_field_name="key",
    required=False,
    initial=0,
  )
  # We don't use multiple but use it as a hack so it has no blank options
  column = LabelSelectionMultipleField(
    queryset=DataTableColumn.objects.all().order_by("key"),
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
    self.full_clean()
    hazard = self.cleaned_data.get("hazard")

    # Allow threshold field to use units from selected hazard
    self.fields["threshold"].hazard = hazard

    self.fields["column"].queryset = self.fields["column"].queryset.filter(hazard=hazard)

    children = ["exposure", "return_period", "threshold"]

    column_filter = {}

    for child in children:
      val = self.cleaned_data.get(child)
      child_filter = {}

      if val is not None:
        column_filter[child] = val

      for sibling in children:
        if child != sibling and self.cleaned_data.get(sibling) is not None:
          child_filter[sibling] = self.cleaned_data.get(sibling)

      self.fields[child].queryset = (
        self.fields[child]
        .queryset.filter(datatablecolumn__in=self.fields["column"].queryset.filter(**child_filter))
        .distinct()
      )

      count = self.fields[child].queryset.count()
      if count == 0:
        self.fields[child].widget = self.fields[child].hidden_widget()
      elif count == 1:
        self.fields[child].widget
    if len(column_filter.keys()):
      self.fields["column"].queryset = self.fields["column"].queryset.filter(**column_filter)

    if self.fields["column"].queryset.count() == 1:
      self.cleaned_data["column"] = self.fields["column"].queryset[0:1]

    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.disable_csrf = True
    self.helper.label_class = "col-12"
    self.helper.field_class = "col-12 pb-0"
    self.helper.layout = Layout(
      "hazard",
      "return_period",
      "threshold",
      "exposure",
    )
