from django import template
from django.shortcuts import get_object_or_404

from data.models import DataTableColumn

register = template.Library()


MAX_OVERLAP_KEY = "max_overlap"
MAX_COMBINED_KEY = "max_combined"
SUMMARY_COLUMNS = set([MAX_OVERLAP_KEY, MAX_COMBINED_KEY])

SummaryColumnContent = {
  MAX_OVERLAP_KEY: {
    "key": MAX_OVERLAP_KEY,
    "label": "Max overlapping exposure",
    "description": "The maximum exposure that is affected by both selected hazard datasets. I.e., the minimum of the selected datasets for each region. Only available when two datasets with matching exposure types are displayed in the table.",
  },
  MAX_COMBINED_KEY: {
    "key": MAX_COMBINED_KEY,
    "label": "Maximum combined exposure",
    "description": "The maximum total exposure that is affected by both selected hazard datasets. I.e., the combined value of the exposure from each hazard set for each region, or the total possible exposure for that region, whichever is lesser. Only available when two datasets with matching exposure types are displayed in the table.",
  },
}


@register.inclusion_tag("tag_templates/show_column_details.html")
def show_column_details(
  key: str,
  pinned=None,
  pinned_keys=None,
):
  column = None
  summary_column = False
  if key and key != "":
    if key in SUMMARY_COLUMNS:
      column = SummaryColumnContent[key]
      summary_column = True
    else:
      column = get_object_or_404(DataTableColumn, key=key) if (key and key != "") else None

  if not column:
    return None

  return {
    "column": column,
    "pinned": pinned,
    "pinned_keys": pinned_keys,
    "summary_column": summary_column,
  }
