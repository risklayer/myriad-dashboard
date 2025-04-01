from enum import StrEnum

from data.models import DataTableColumn, VulnerabilityCurve

PinType = StrEnum("PinType", {"CURVE": "curve", "EXPOSURE": "exposure"})

# TODO let this be configured by each app
ButtonConfigs = {
  "curve": {
    "list_title": "Pinned curves",
    "actions_template": "curve_explorer/pin_actions.html",
    "model": VulnerabilityCurve,
    "dropdown": True,
  },
  "exposure": {
    "list_title": "Pinned datasets",
    "actions_template": "exposure_at_risk/pin_actions.html",
    "model": DataTableColumn,
    "return_list_button": True,
    "add_to_table": True,
  },
}


def get_option(pin_type: PinType, option: str):
  return ButtonConfigs[pin_type].get(option, None)


def init_pin_session(request, pin_type: PinType):
  if "pinned_" + pin_type not in request.session:
    request.session["pinned_" + pin_type] = list()


def get_pinned(request, pin_type: PinType):
  init_pin_session(request, pin_type)
  return request.session["pinned_" + pin_type]


def remove_pin(request, pin_type: PinType, key: str, save: bool, include_items: bool):
  init_pin_session(request, pin_type)
  for pin_tuple in request.session["pinned_" + pin_type]:
    if pin_tuple[0] == key:
      request.session["pinned_" + pin_type].remove(pin_tuple)
      break
  if save:
    request.session.save()
  pinned = request.session["pinned_" + pin_type]
  keys = get_pinned_keys(pinned)
  if include_items:
    pinned = append_pinned_items(pinned, pin_type)
  return pinned, keys


def add_pin(request, pin_type: PinType, key: str, label: str):
  init_pin_session(request, pin_type)
  model = get_option(pin_type, "model")
  item = model.objects.get(key=key)

  name = item.label
  remove_pin(request, pin_type, key, False, False)
  request.session["pinned_" + pin_type].append((key, name, label))
  request.session.save()
  pinned = request.session["pinned_" + pin_type]
  keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, pin_type)
  return pinned, keys


def get_pinned_keys(pinned):
  pinned_keys = []
  for key, name, label in pinned:
    pinned_keys.append(key)
  return pinned_keys


def append_pinned_items(pinned, pin_type: PinType):
  model = get_option(pin_type, "model")
  keys = get_pinned_keys(pinned)
  items_map = {o.key: o for o in model.objects.filter(key__in=keys)}
  items = [(key, name, label, items_map[key]) for (key, name, label) in pinned]
  return items


def get_pin_label(pinned, key: str):
  for pin_key, _, label, _ in pinned:
    if pin_key == key:
      return label
  return ""
