import re
from django import template
from django.template.defaultfilters import stringfilter

from shared.pin import get_pin_label
from shared.utils import float_to_3_digits

register = template.Library()


@register.filter
@stringfilter
def desnake(value):
  return value.replace("_", " ").strip()


@register.filter(name="not_value")
def not_value(true_value):
  return not true_value


@register.filter(name="equals")
def equals(first, second):
  return first == second


@register.filter(name="pin_label")
def pin_label(pinned, key):
  return get_pin_label(pinned, key)


@register.filter(name="simplify_float")
def simplify_float(value):
  return float_to_3_digits(value) if isinstance(value, (int, float)) else value


@register.filter(name="fix_danube_columns")
def fix_danube_columns(value):
  return re.sub(
    "\\beq\\b",
    "Earthquake",
    re.sub(
      "\\b(flood|fl)\\b",
      "Flood",
      re.sub(
        "\\btotal\\b", "Total", re.sub("^fp\\s(.+)$", "\\1 Footprint", re.sub("_", " ", value))
      ),
    ),
  )
