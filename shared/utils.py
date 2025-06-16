from functools import reduce


def float_to_3_digits(value: float | int) -> str:
  if isinstance(value, str):
    return value
  if value > 100:
    return str(round(value, 0))

  if value > 10:
    return str(round(value, 1))

  if value > 1:
    return str(round(value, 2))

  if value > 0.1:
    return str(round(value, 3))

  if value > 0.01:
    return str(round(value, 4))

  if value > 0.001:
    return str(round(value, 5))

  if value > 0.0001:
    return str(round(value, 6))

  if value == 0:
    return "0"

  return "{:e}".format(value)


def make_choices(items: list, include_blank=True, sort=True, blank: str = "Please select"):
  choices = [(x, x if x else blank) for x in (sorted(items) if sort else items)]
  return [(None, "")] + choices if include_blank else choices


def rgetattr(obj, attr, *args):
  def _getattr(obj, attr):
    return getattr(obj, attr, *args)

  return reduce(_getattr, [obj] + attr.split("."))
