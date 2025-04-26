from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
  Layout,
  Reset,
)
from django.forms import (
  Form,
)
from django.forms.fields import (
  ChoiceField,
)
from data.models import (
  CurveConstructionType1,
  CurveConstructionType2,
  CurveConstructionType3,
  CurveCoverage,
  Hazard,
  CurveOccupancyType1,
  CurveOccupancyType2,
  CurveOccupancyType3,
  CurveQuality,
  CurveSector,
  Country,
  get_curve_field_label,
  VulnerabilityCurve,
)
from shared.form_fields import LabelSelectionField
from shared.utils import make_choices


class CurveExplorerFilterForm(Form):
  hazard = LabelSelectionField(
    queryset=Hazard.objects.filter(
      vulnerabilitycurve__in=VulnerabilityCurve.objects.all()
    ).distinct(),
    empty_label="",
    to_field_name="key",
    required=False,
  )
  countries = LabelSelectionField(
    queryset=Country.objects.all(),
    empty_label="",
    to_field_name="country_code",
    required=False,
  )
  quality = LabelSelectionField(
    queryset=CurveQuality.objects.all(),
    empty_label="",
    to_field_name="key",
    required=False,
  )
  con_description_1 = LabelSelectionField(
    queryset=CurveConstructionType1.objects.all(),
    empty_label="",
    to_field_name="key",
    required=False,
  )
  con_description_2 = LabelSelectionField(
    queryset=CurveConstructionType2.objects.all(),
    empty_label="",
    to_field_name="key",
    required=False,
  )
  con_description_3 = LabelSelectionField(
    queryset=CurveConstructionType3.objects.all(),
    empty_label="",
    to_field_name="key",
    required=False,
  )
  occ_description_1 = LabelSelectionField(
    queryset=CurveOccupancyType1.objects.all(),
    empty_label="",
    to_field_name="key",
    required=False,
  )
  occ_description_2 = LabelSelectionField(
    queryset=CurveOccupancyType2.objects.all(),
    empty_label="",
    to_field_name="key",
    required=False,
  )
  occ_description_3 = LabelSelectionField(
    queryset=CurveOccupancyType3.objects.all(),
    empty_label="",
    to_field_name="key",
    required=False,
  )
  coverage = LabelSelectionField(
    queryset=CurveCoverage.objects.all(),
    empty_label="",
    to_field_name="key",
    required=False,
  )
  myriad_sectors_applicable = LabelSelectionField(
    queryset=CurveSector.objects.all(),
    empty_label="",
    to_field_name="key",
    required=False,
  )

  def __init__(self, *args, panel: int, **kwargs):
    auto_id = "id_panel_" + str(panel) + "_%s"
    super(CurveExplorerFilterForm, self).__init__(*args, auto_id=auto_id, **kwargs)
    for field in self:
      field.label = get_curve_field_label(field.name)
    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.form_class = "form-horizontal"
    self.helper.label_class = "col-12 col-sm-3 col-md-12 col-lg-4 col-xxxl-12 text-sm-end text-md-start text-lg-end text-xxxl-start"
    self.helper.field_class = "col-12 col-sm-9 col-md-12 col-lg-8 col-xxxl-12"
    self.helper.layout = Layout(
      "hazard",
      "countries",
      "quality",
      "con_description_1",
      "con_description_2",
      "con_description_3",
      "occ_description_1",
      "occ_description_2",
      "occ_description_3",
      "coverage",
      "myriad_sectors_applicable",
      Reset("", "Reset", css_class="btn btn-secondary float-end"),
    )


class CurveExplorerRowForm(Form):
  row = ChoiceField(
    required=False,
    choices=(),
    label="Choose a curve",
  )

  def update_choices(self, possible_values: dict):
    for key, values in possible_values.items():
      if key in self.fields:
        if key != "row":
          self.fields[key].choices = make_choices(values)

  def __init__(
    self,
    *args,
    panel: int,
    possible_values: list = [],
    empty_message: str = "Please select a filter to choose a curve",
    **kwargs,
  ):
    auto_id = "id_panel_" + str(panel) + "_%s"
    kwargs.pop("panel", None)
    kwargs.pop("possible_values", None)
    kwargs.pop("empty_message", None)
    super(CurveExplorerRowForm, self).__init__(*args, auto_id=auto_id, **kwargs)
    self.helper = FormHelper()
    self.helper.form_tag = False
    self.update_row_options(possible_values, empty_message)

  def update_row_options(
    self, choices: list[str], empty_message="Please select a filter to choose a curve"
  ):
    if len(choices):
      self.fields["row"].choices = choices
    else:
      self.fields["row"].choices = [(None, empty_message)]
      self.fields["row"].disabled = True

  def clean(self):
    if "row" in self.errors:
      del self.errors["row"]
    row = self.data.get("row")
    choices = self.fields["row"].choices
    if len(choices):
      rows = [x[0] for x in choices]
      if row is None or row == "" or row not in rows:
        self.cleaned_data["row"] = rows[0]
      else:
        self.cleaned_data["row"] = self.cleaned_data["row"]
    else:
      del self.cleaned_data["row"]
    return self.cleaned_data
