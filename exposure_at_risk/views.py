from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from data.models import Country
from exposure_at_risk.exposure_at_risk_form import (
  ExposureAtRiskRegionsForm,
  ExposureAtRiskSettingsForm,
)
from shared.pin import PinType, append_pinned_items, get_pinned, get_pinned_keys


# Centre of Europe
DEFAULT_LATITUDE = 54.5260
DEFAULT_LONGITUDE = 15.2551


@require_GET
def index(request):
  template = "exposure_at_risk/index.html"

  column = request.GET.get("column") or None
  table_column = request.GET.getlist("table_column") or None

  pinned = get_pinned(request, PinType.EXPOSURE)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.EXPOSURE)

  settings_form = ExposureAtRiskSettingsForm(request.GET or request.POST)
  regions_form = ExposureAtRiskRegionsForm(request.GET or request.POST)
  countries_root = regions_form.create_countries_hierarchy()

  return render(
    request,
    template,
    {
      "latitude": DEFAULT_LATITUDE,
      "longitude": DEFAULT_LONGITUDE,
      "countries": [countries_root],
      "column": column,
      "table_column": table_column,
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

  return render(
    request,
    template,
    {
      "pinned": pinned,
      "pinned_keys": pinned_keys,
    },
  )
