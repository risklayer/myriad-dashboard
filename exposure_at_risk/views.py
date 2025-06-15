from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from data.models import DataTableColumn
from scenario_calculator.config import DEFAULT_LATITUDE
from shared.pin import PinType, append_pinned_items, get_pinned, get_pinned_keys
from scenario_calculator.config import DEFAULT_LONGITUDE
from shared.shared_forms import MapSettingsForm, RegionsForm


@require_GET
def index(request):
  template = "exposure_at_risk/index.html"

  column = request.GET.get("column", None)

  if column:
    column_obj = DataTableColumn.objects.filter(key=column).first()
    if not column_obj:
      column = None

  table_columns = request.GET.getlist("table_columns") or None

  pinned = get_pinned(request, PinType.EXPOSURE)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.EXPOSURE)

  settings_form = MapSettingsForm(request.GET)
  regions_form = RegionsForm(request.GET or request.POST)
  countries_root = regions_form.create_countries_hierarchy()

  return render(
    request,
    template,
    {
      "latitude": DEFAULT_LATITUDE,
      "longitude": DEFAULT_LONGITUDE,
      "countries": [countries_root],
      "column": column,
      "table_columns": table_columns,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "settings_form": settings_form,
    },
  )


@require_GET
def column_details(request, key: str):
  template = "exposure_at_risk/column_details.html"

  pinned = get_pinned(request, PinType.EXPOSURE)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.EXPOSURE)

  if key:
    get_object_or_404(DataTableColumn, key=key)

  return render(
    request,
    template,
    {
      "key": key,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
    },
  )


@require_POST
def refine_form(request):
  template = "exposure_at_risk/refine_form.html"

  pinned = get_pinned(request, PinType.EXPOSURE)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.EXPOSURE)

  column = request.POST.get("column", None)

  if column:
    get_object_or_404(DataTableColumn, key=column)

  return render(
    request,
    template,
    {
      "column": column,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
    },
  )
