from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
  Fieldset,
  Layout,
  Reset,
)
from django.forms import (
  Form,
)
from django.forms.fields import (
  ChoiceField,
)


def make_choices(items: set, include_blank=True, blank: str = "Please select"):
  choices = [(x, x if x else blank) for x in sorted(items)]
  return [(None, "")] + choices if include_blank else choices


class BoilerplateFilterForm(Form):
  def update_choices(self, possible_values: dict):
    for key, values in possible_values.items():
      if key in self.fields:
        self.fields[key].choices = make_choices(values)

  def __init__(self, *args, **kwargs):
    super(BoilerplateFilterForm, self).__init__(*args, **kwargs)
    self.helper = FormHelper()
    self.helper.form_tag = False
    self.helper.form_class = "form-horizontal"
    self.helper.label_class = "col-md-3 col-xxl-12 text-md-end text-xxl-start"
    self.helper.field_class = "col-md-9 col-xxl-12"
    self.helper.layout = Layout()
