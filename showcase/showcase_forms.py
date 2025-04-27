from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
  Layout,
)
from django.forms import (
  ChoiceField,
  Form,
  Select,
)

from data.models import (
  DataTableColumnMetadataValueString,
  Hazard,
)
from shared.form_fields import (
  LabelSelectionField,
)
from shared.utils import make_choices


class ShowcaseFilterForm(Form):
  hazard = LabelSelectionField(
    queryset=Hazard.objects.filter(key__in=list(["EQ", "flood", "EQ_flood"]))
    .distinct()
    .order_by("id"),
    empty_label=None,
    to_field_name="key",
    required=False,
    blank=False,
    initial="EQ_flood",
    widget=Select(
      {
        "onchange": "formUpdate()",
      }
    ),
  )
  column = ChoiceField(
    label="NACE Rev 2.1 code",
    choices=list(),
    # empty_label="",
    # to_field_name="key",
    required=False,
    initial=("A21_A", "A21_A"),
    # initial=0,
  )

  def __init__(self, *args, **kwargs):
    super(ShowcaseFilterForm, self).__init__(*args, **kwargs)

    self.fields["column"].choices = make_choices(
      DataTableColumnMetadataValueString.objects.filter(metadata__key="nace_code")
      .values_list("value", flat=True)
      .distinct()
      .order_by("value"),
      include_blank=False,
    )

    # meta_field_names = self.configure_fields()

    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.disable_csrf = True
    self.helper.label_class = "col-12"
    self.helper.field_class = "col-12 pb-0"
    self.helper.layout = Layout(
      "hazard",
      # "column",
      #   *meta_field_names,
    )
