import json

from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .curve_editor_form import CurveEditorFilterForm, CurveEditorRowForm

from data.api import api_curves_filter_json
from data.models import VulnerabilityCurve

from data.models import VulnerabilityCurve


def init_pin_session(request):
  if "pinned_curves" not in request.session:
    request.session["pinned_curves"] = list()


def get_pinned_curves(request):
  init_pin_session(request)
  return request.session["pinned_curves"]


def add_pin(request, key: str, label: str):
  init_pin_session(request)
  curve = VulnerabilityCurve.objects.get(key=key)

  name = curve.label
  remove_pin(request, key, False)
  request.session["pinned_curves"].append((key, name, label))
  request.session.save()
  return request.session["pinned_curves"], get_pinned_keys(request.session["pinned_curves"])


def remove_pin(request, key: str, save: bool):
  init_pin_session(request)
  for pin_tuple in request.session["pinned_curves"]:
    if pin_tuple[0] == key:
      request.session["pinned_curves"].remove(pin_tuple)
      break
  if save:
    request.session.save()
  return request.session["pinned_curves"], get_pinned_keys(request.session["pinned_curves"])


def get_pinned_keys(pinned):
  pinned_keys = []
  for key, name, label in pinned:
    pinned_keys.append(key)
  return pinned_keys


def get_pin_label(pinned, key: str):
  for pin_key, name, label in pinned:
    if pin_key == key:
      return label
  return ""


@require_GET
def index(request):
  template = "curve_editor/index.html"

  forms = []
  for i in [0, 1]:
    filter_form = CurveEditorFilterForm(panel=i)
    curve_form = CurveEditorRowForm(panel=i)
    curve_form.update_row_options([], "Please select a filter before choosing a curve")
    forms.append((i, filter_form, curve_form))

  pinned = get_pinned_curves(request)
  pinned_keys = get_pinned_keys(pinned)
  panel = 1

  return render(
    request,
    template,
    {
      "forms": forms,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "panel": panel,
    },
  )


@require_POST
def filter_curves(request):
  if not request.htmx:
    return HttpResponseForbidden()
  template = "curve_editor/filter_curves.html"

  panel = request.POST.get("panel")

  is_filtered = False
  for field in CurveEditorFilterForm(panel=None).fields.keys():
    if request.POST.get(field) != "":
      is_filtered = True
      break

  filtered_row_ids_and_names = []
  if is_filtered:
    curve_data = api_curves_filter_json(request.POST)
    filtered_row_ids_and_names = curve_data["curves"]

  curve_form = CurveEditorRowForm(
    request.POST,
    panel=panel,
    possible_values=filtered_row_ids_and_names,
    empty_message="No curves match the selected criteria"
    if is_filtered
    else "Please select a filter before choosing a curve",
  )

  curve_form.full_clean()

  curve = None
  curve_key = curve_form.cleaned_data.get("row")
  pinned = get_pinned_curves(request)
  pinned_keys = get_pinned_keys(pinned)

  if curve_key and len(filtered_row_ids_and_names):
    curve = VulnerabilityCurve.objects.get(key=curve_key)

  return render(
    request,
    template,
    {
      "curve_form": curve_form,
      "curve": curve,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "panel": panel,
    },
  )


@require_POST
def show_curve(request):
  if not request.htmx:
    return HttpResponseForbidden()
  template = "curve_editor/filter_curves.html"

  pinned = get_pinned_curves(request)
  pinned_keys = get_pinned_keys(pinned)

  curve = VulnerabilityCurve.objects.filter(key=request.POST.get("row", None)).first()
  pin_label = curve.label

  panel = int(request.POST.get("panel") or 1)

  return render(
    request,
    template,
    {
      "curve": curve if curve else None,
      "values": curve if curve else None,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "pin_name": pin_label,
      "panel": panel,
    },
  )


@require_POST
def pin_curve(request):
  if not request.htmx:
    return HttpResponseForbidden()

  key = request.POST.get("key")
  rename = request.POST.get("rename")
  name = request.htmx.prompt or ""
  pinned, pinned_keys = add_pin(request, key, name)
  panel = int(request.POST.get("panel") or 1)
  show_pin_buttons = []
  for i in [0, 1]:
    selected_id = request.POST.get("curve_panel_selected_" + str(i))
    if selected_id and selected_id == key:
      show_pin_buttons.append(i)

  template = "curve_editor/pin.html"
  return render(
    request,
    template,
    {
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "key": key,
      "rename": rename,
      "name": name,
      "show_pin_buttons": show_pin_buttons,
      "panel": panel,
    },
  )


@require_POST
def unpin_curve(request):
  if not request.htmx:
    return HttpResponseForbidden()

  key = request.POST["key"]
  pinned, pinned_keys = remove_pin(request, key, True)
  panel = int(request.POST.get("panel") or 1)
  show_pin_buttons = []
  for i in [0, 1]:
    selected_key = request.POST.get("curve_panel_selected_" + str(i))
    if selected_key and selected_key == key:
      show_pin_buttons.append(i)

  template = "curve_editor/pin.html"
  return render(
    request,
    template,
    {
      "key": key,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "removed": True,
      "show_pin_buttons": show_pin_buttons,
      "panel": panel,
    },
  )
