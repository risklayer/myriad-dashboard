from django import template

from data.models import HrscEvent

register = template.Library()


@register.inclusion_tag("tag_templates/show_event_details.html")
def show_event_details(
  key: int,
  pinned=None,
  pinned_keys=None,
):
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
  }
