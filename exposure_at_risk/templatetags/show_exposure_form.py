from django import template

from exposure_at_risk.exposure_at_risk_forms import (
  ExposureAtRiskFilterForm,
)

register = template.Library()


@register.inclusion_tag("tag_templates/show_exposure_form.html")
def show_exposure_form(
  request,
  column: str,
  pinned=None,
  pinned_keys=None,
):
  filter_form = ExposureAtRiskFilterForm(request.GET or request.POST or None)

  return {
    "request": request,
    "column": column,
    "filter_form": filter_form,
    "pinned": pinned,
    "pinned_keys": pinned_keys,
  }
