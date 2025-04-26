from django import template

from scenario_calculator.scenario_calculator_forms import (
  ScenarioCalculatorHazardFilterForm,
)

register = template.Library()


@register.inclusion_tag("tag_templates/show_scenario_form.html")
def show_scenario_form(
  request,
  filter_form: ScenarioCalculatorHazardFilterForm,
  pinned=None,
  pinned_keys=None,
  event=None,
):
  return {
    "filter_form": filter_form,
    "event": event,
    "pinned": pinned,
    "pinned_keys": pinned_keys,
  }
