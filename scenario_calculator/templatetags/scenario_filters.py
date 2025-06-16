from django import template

from scenario_calculator.config import non_filter_keys


register = template.Library()


@register.filter(name="filter_event_metadata")
def filter_event_metadata(pairs: list[tuple[str, str]]):
  result = [(k, v) for k, v in pairs if k not in non_filter_keys]
  return result
