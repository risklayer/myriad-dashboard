from django import template

from data.models import HrscEvent

register = template.Library()


# MAX_OVERLAP_KEY = "max_overlap"
# MAX_COMBINED_KEY = "max_combined"
# SUMMARY_COLUMNS = set([MAX_OVERLAP_KEY, MAX_COMBINED_KEY])

# SummaryColumnContent = {
#   MAX_OVERLAP_KEY: {
#     "key": MAX_OVERLAP_KEY,
#     "label": "Max overlapping exposure",
#     "description": "The maximum exposure that is affected by both selected hazard events. I.e., the minimum of the selected events for each region. Only available when two events with matching exposure types are displayed in the table.",
#   },
#   MAX_COMBINED_KEY: {
#     "key": MAX_COMBINED_KEY,
#     "label": "Maximum combined exposure",
#     "description": "The maximum total exposure that is affected by both selected hazard events. I.e., the combined value of the exposure from each hazard set for each region, or the total possible exposure for that region, whichever is lesser. Only available when two events with matching exposure types are displayed in the table.",
#   },
# }


@register.inclusion_tag("tag_templates/show_event_details.html")
def show_event_details(
  key: int,
  pinned=None,
  pinned_keys=None,
):
  # event = None
  # summary_column = False
  # if key and key != "":
  #   if key in SUMMARY_COLUMNS:
  #     event = SummaryColumnContent[key]
  #     summary_column = True
  #   else:
  #     event = DataTableColumn.objects.filter(key=key).first() if (key and key != "") else None
  event = (
    HrscEvent.objects.filter(id=int(key)).select_related("collection", "collection__hazard").first()
    if (key and key != "")
    else None
  )

  if not event:
    return None

  return {
    "event": event,
    "pinned": pinned,
    "pinned_keys": pinned_keys,
    # "summary_event": summary_event,
  }
