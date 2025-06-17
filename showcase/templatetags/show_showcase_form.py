from django import template

from showcase.showcase_forms import (
  ShowcaseFilterForm,
)

register = template.Library()


@register.inclusion_tag("tag_templates/show_showcase_form.html")
def show_showcase_form(
  request,
  column: str,
  filter_form: ShowcaseFilterForm,
):
  return {
    "request": request,
    "column": column,
    "filter_form": filter_form,
  }
