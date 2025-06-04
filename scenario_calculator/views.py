from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from data.models import Hazard, HrscEvent, HrscHazardProbabilityRasterInstance
from scenario_calculator.config import (
  DEFAULT_LATITUDE,
  DEFAULT_LONGITUDE,
  WINTERSTORM_MAXIMUM_RADIUS,
  DEFAULT_RADIUS,
)
from scenario_calculator.scenario_calculator_forms import (
  ScenarioCalculatorCombineEventsForm,
  ScenarioCalculatorHazardFilterForm,
  ScenarioCalculatorProbabilityForm,
  ScenarioCalculatorProbabilitySharedForm,
)
from shared.pin import PinType, append_pinned_items, get_pinned, get_pinned_keys
from shared.shared_forms import MapSettingsForm, RegionsForm
from shared.utils import float_to_3_digits


@require_GET
def index(request):
  template = "scenario_calculator/index.html"

  event_id = request.GET.get("event", "")

  if event_id is None or event_id == "" or HrscEvent.objects.filter(id=int(event_id)).count() < 1:
    event_id = ""

  table_event_ids = request.GET.getlist("table_events")

  table_events = (
    list(HrscEvent.objects.filter(id__in=table_event_ids)) if len(table_event_ids) else list()
  )

  pinned = get_pinned(request, PinType.EVENT)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.EVENT)

  settings_form = MapSettingsForm(request.GET)
  regions_form = RegionsForm(request.GET)
  filter_form = (
    ScenarioCalculatorHazardFilterForm(
      {k: request.GET[k] for k in request.GET if k != "event"},
    )
    if request.GET
    else ScenarioCalculatorHazardFilterForm()
  )

  probability_forms = [
    ScenarioCalculatorProbabilityForm(request.GET or None, prefix=f"p{i}") for i in range(1, 3)
  ]

  probability_shared_form = ScenarioCalculatorProbabilitySharedForm(
    request.GET or None,
    prefix="p",
    initial={
      "latitude": DEFAULT_LATITUDE,
      "longitude": DEFAULT_LONGITUDE,
      "time_window": 1,
      "time_window_unit": ("weeks", "Weeks"),
    },
  )

  combine_events_form = (
    ScenarioCalculatorCombineEventsForm(request.GET)
    if request.GET.get("exposure")
    else ScenarioCalculatorCombineEventsForm()
  )

  countries_root = regions_form.create_countries_hierarchy()

  return render(
    request,
    template,
    {
      "latitude": DEFAULT_LATITUDE,
      "longitude": DEFAULT_LONGITUDE,
      "radius": DEFAULT_RADIUS,
      "data_winterstorm_radius": WINTERSTORM_MAXIMUM_RADIUS,
      "countries": [countries_root],
      "event": event_id,
      "table_events": table_events,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "filter_form": filter_form,
      "settings_form": settings_form,
      "probability_forms": probability_forms,
      "probability_shared_form": probability_shared_form,
      "combine_events_form": combine_events_form,
    },
  )


@require_GET
def event_details(request, key: str):
  template = "scenario_calculator/event_details.html"

  pinned = get_pinned(request, PinType.EVENT)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.EVENT)

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
def refine_events_form(request):
  template = "tag_templates/show_scenario_form.html"

  pinned = get_pinned(request, PinType.EVENT)
  pinned_keys = get_pinned_keys(pinned)
  pinned = append_pinned_items(pinned, PinType.EVENT)

  filter_form = ScenarioCalculatorHazardFilterForm(request.POST)

  event = request.POST.get("event") or ""

  return render(
    request,
    template,
    {
      "zoom": False,
      "event": event,
      "pinned": pinned,
      "pinned_keys": pinned_keys,
      "filter_form": filter_form,
    },
  )


@require_POST
def probability_refine(request):
  template = "scenario_calculator/probability_hazard_form.html"

  panel = int(request.POST.get("panel"))

  form = ScenarioCalculatorProbabilityForm(request.POST, prefix=f"p{panel}")

  return render(
    request,
    template,
    {
      "form": form,
      "panel": panel,
    },
  )


@require_POST
def probability_result(request):
  template = "scenario_calculator/probability_result.html"

  probability_forms = [
    ScenarioCalculatorProbabilityForm(request.POST, prefix=f"p{i}") for i in range(1, 3)
  ]

  probability_shared_form = ScenarioCalculatorProbabilitySharedForm(
    request.POST,
    prefix="p",
  )

  results = list()
  references = list()
  if probability_shared_form.is_valid():
    latitude = probability_shared_form.cleaned_data.get("latitude")
    longitude = probability_shared_form.cleaned_data.get("longitude")
    time_window = probability_shared_form.cleaned_data.get("time_window")
    time_window_unit = probability_shared_form.cleaned_data.get("time_window_unit")
    if time_window_unit == "months":
      time_window = time_window / 12
    elif time_window_unit == "days":
      time_window = time_window / 365.25
    # time_window_delta = datetime.timedelta(days= time_window)
    # (time window/return period 1) * (time window/return period 2)
    for form in probability_forms:
      if form.is_valid():
        hazard: Hazard = form.cleaned_data.get("hazard")
        severity: HrscHazardProbabilityRasterInstance = form.cleaned_data.get("severity")
        if not severity:
          return render(
            request,
            template,
            {
              "results": None,
              "probability_shared_form": probability_shared_form,
            },
          )
        result = severity.get_probability_value(latitude=latitude, longitude=longitude)
        # delta = datetime.timedelta(days=time_window / result)
        return_period = 1 / result if result else "-"
        results.append(
          (
            hazard.label,
            severity.label,
            result,
            return_period,
            float_to_3_digits(return_period) + " years",
          )
        )
        if severity.probability_raster.references and len(severity.probability_raster.references):
          references = [*references, *severity.probability_raster.references]

  if len(results) == 2:
    combination = results[0][2] * results[1][2]
    if combination:
      return_period = (1 / time_window) * (1 / (combination))
      if return_period > 100:
        return_period = int(return_period)
    else:
      return_period = "-"
    # delta = datetime.timedelta(days=total)
    results.append(
      ("Combined", "—", "", return_period, float_to_3_digits(return_period) + " years")
    )

  return render(
    request,
    template,
    {
      "results": results,
      "probability_shared_form": probability_shared_form,
      "references": references,
    },
  )
