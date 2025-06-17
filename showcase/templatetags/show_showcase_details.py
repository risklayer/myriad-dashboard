from django import template

from data.models import DataTableColumn

register = template.Library()


@register.inclusion_tag("tag_templates/show_showcase_details.html")
def show_showcase_details(
  hazard: str | None,
  exposure: str | None,
):
  if not hazard or not exposure:
    return None

  filter = (
    {"key": exposure.lower() + "_" + ("fl" if hazard == "flood" else "eq")}
    if exposure.startswith("fp")
    else {
      "datatablecolumnmetadatavaluestring__value": exposure,
      "datatablecolumnmetadatavaluestring__metadata__key": "nace_code",
    }
  )
  column = DataTableColumn.objects.filter(hazard__key=hazard, **filter).first()

  if not column:
    return None

  return {
    "column": column,
    "hazard": hazard,
    "exposure": exposure,
  }
