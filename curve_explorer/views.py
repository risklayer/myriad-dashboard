from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST


from shared.pin import PinType, append_pinned_items, get_pinned, get_pinned_keys
from data.curves import curves_filter_json
from data.models import VulnerabilityCurve

from .curve_explorer_form import CurveExplorerFilterForm, CurveExplorerRowForm


@require_GET
def index(request):
  template = "curve_explorer/index.html"

  forms = []
  for i in [0, 1]:
    filter_form = CurveExplorerFilterForm(panel=i)
    curve_form = CurveExplorerRowForm(panel=i)
    curve_form.update_row_options([], "Please select a filter before choosing a curve")
    forms.append((i, filter_form, curve_form))

  pinned = get_pinned(request, PinType.CURVE)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.CURVE)
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
  template = "curve_explorer/filter_curves.html"

  panel = request.POST.get("panel")

  is_filtered = False
  for field in CurveExplorerFilterForm(panel=None).fields.keys():
    if request.POST.get(field) != "":
      is_filtered = True
      break

  filtered_row_ids_and_names = []
  if is_filtered:
    curve_data = curves_filter_json(request.POST)
    filtered_row_ids_and_names = curve_data["curves"]

  curve_form = CurveExplorerRowForm(
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
  pinned = get_pinned(request, PinType.CURVE)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.CURVE)

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
  template = "curve_explorer/filter_curves.html"

  pinned = get_pinned(request, PinType.CURVE)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.CURVE)

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
