from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
  Layout,
)
from django.forms import (
  BooleanField,
  CharField,
  CheckboxInput,
  ChoiceField,
  Form,
  HiddenInput,
  Select,
  SelectMultiple,
)

from data.models import (
  Country,
)
from shared.form_fields import LabelSelectionMultipleField, brewer_colors, brewer_colors_list
from shared.utils import make_choices


quantisation_methods = [
  ("logarithmic", "Logarithmic"),
  ("equidistant", "Equidistant"),
  ("quantile", "Quantile"),
  ("k-means", "K-means"),
]


class MapSettingsForm(Form):
  quantisation = ChoiceField(
    required=False,
    choices=quantisation_methods,
    initial=("logarithmic", "Logarithmic"),
    widget=Select(
      {
        "onchange": "formUpdate()",
      }
    ),
  )
  colors = ChoiceField(
    required=False,
    choices=make_choices(
      brewer_colors,
      include_blank=False,
      sort=False,
    ),
    initial=("RdYlGn", "RdYlGn"),
  )
  invert_colors = BooleanField(
    label="Invert colours",
    initial=False,
    required=False,
    widget=CheckboxInput(
      {
        "onchange": "formUpdate()",
      }
    ),
  )
  base_layer = CharField(widget=HiddenInput(), required=False)

  brewer_colors_list = brewer_colors_list

  def __init__(self, *args, **kwargs):
    super(MapSettingsForm, self).__init__(*args, **kwargs)
    self.full_clean()
    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.disable_csrf = True
    self.helper.label_class = "col-12"
    self.helper.field_class = "col-12 pb-0"
    self.helper.layout = Layout("quantisation", "invert_colors", "base_layer")


class RegionsForm(Form):
  countries = LabelSelectionMultipleField(
    queryset=Country.objects.all().order_by("label"),
    to_field_name="country_code",
    required=False,
    initial=["ALL"],
    widget=SelectMultiple(
      {
        "onchange": "formUpdate()",
      }
    ),
  )

  def create_countries_hierarchy(self, codes: list[str] = None):
    countries = Country.objects.order_by("label").prefetch_related("areas").order_by("label")
    if codes:
      countries = countries.filter(country_code__in=codes)

    if self.is_bound:
      selected_countries = set(self.data.getlist("countries"))
      selected_areas = set(self.data.getlist("areas"))
    else:
      selected_countries = set(self.initial.get("countries"))
      selected_areas = set(self.initial.get("areas"))
    all_selected = "ALL" in selected_countries
    # regions = Nuts3Area.objects.all().order_by("label")
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
