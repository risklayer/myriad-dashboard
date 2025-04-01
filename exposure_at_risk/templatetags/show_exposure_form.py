from django import template

from exposure_at_risk.exposure_at_risk_form import (
  ExposureAtRiskFilterForm,
)

register = template.Library()


@register.inclusion_tag("tag_templates/show_exposure_form.html")
def show_exposure_form(
  request,
  pinned=None,
  pinned_keys=None,
):
  filter_form = ExposureAtRiskFilterForm(request.GET or request.POST)

  return {
    "filter_form": filter_form,
    "pinned": pinned,
    "pinned_keys": pinned_keys,
  }
