from django import template
from django.template.defaultfilters import stringfilter

from shared.pin import get_pin_label

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


# @register.filter(name="contains")
# def contains(first, second):
#   return first == second
