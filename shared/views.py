from shared.pin import (
  PinType,
  add_pin,
  get_option,
  remove_pin,
)


from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render
from django.views.decorators.http import require_POST


@require_POST
def pin(request, pin_type: PinType):
  if not request.htmx:
    return HttpResponseForbidden()
  if pin_type not in [e.value for e in PinType]:
    return HttpResponseNotFound("Unsupported pin type")

  key = request.POST.get("key")
  rename = request.POST.get("rename")
  name = request.htmx.prompt or ""
  pinned, pinned_keys = add_pin(request, pin_type, key, name)
  panel = int(request.POST.get("panel") or 1)
  show_panel_pin_buttons = []
  for i in [0, 1]:
    selected_key = request.POST.get("item_selected_" + str(i))
    if selected_key and selected_key == key:
      show_panel_pin_buttons.append(i)

  label = None
  for k, _name, item_label, _item in pinned:
    if k == key:
      label = item_label

  template = "shared/pin.html"
  return render(
    request,
    template,
    {
      "key": key,
      "label": label,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "rename": rename,
      "name": name,
      "show_panel_pin_buttons": show_panel_pin_buttons,
      "panel": panel,
      "pin_type": pin_type,
      "list_title": get_option(pin_type, "list_title"),
      "actions_template": get_option(pin_type, "actions_template"),
      "return_list_button": get_option(pin_type, "return_list_button"),
      "add_to_table": get_option(pin_type, "add_to_table"),
      "dropdown": get_option(pin_type, "dropdown"),
    },
  )


@require_POST
def unpin(request, pin_type: PinType):
  if not request.htmx:
    return HttpResponseForbidden()
  if pin_type not in [e.value for e in PinType]:
    return HttpResponseNotFound("Unsupported pin type")

  key = request.POST["key"]
  pinned, pinned_keys = remove_pin(request, pin_type, key, True, True)
  panel = int(request.POST.get("panel") or 1)
  show_panel_pin_buttons = []
  for i in [0, 1]:
    selected_key = request.POST.get("item_selected_" + str(i))
    if selected_key and selected_key == key:
      show_panel_pin_buttons.append(i)

  template = "shared/pin.html"
  return render(
    request,
    template,
    {
      "key": key,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "removed": True,
      "show_panel_pin_buttons": show_panel_pin_buttons,
      "panel": panel,
      "pin_type": pin_type,
      "list_title": get_option(pin_type, "list_title"),
      "actions_template": get_option(pin_type, "actions_template"),
      "return_list_button": get_option(pin_type, "return_list_button"),
      "add_to_table": get_option(pin_type, "add_to_table"),
      "dropdown": get_option(pin_type, "dropdown"),
    },
  )
