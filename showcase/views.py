from django.shortcuts import render
from django.views.decorators.http import require_GET

from shared.shared_forms import MapSettingsForm, RegionsForm
from showcase.showcase_forms import ShowcaseFilterForm

displayed_countries = [
  "BA",
  "MD",
  "BG",
  "AT",
  "DE",
  "CZ",
  "HU",
  "RO",
  "PL",
  "RS",
  "SK",
  # "TR",
]

DEFAULT_LATITUDE = 48.5312
DEFAULT_LONGITUDE = 19.3829


@require_GET
def index(request):
  template = "showcase/index.html"

  column = request.GET.get("column") or None
  table_columns = request.GET.getlist("table_columns") or None

  if table_columns and len(table_columns):
    a_to_s = [chr(c) for c in range(65, 84)]
    table_columns = [col for col in table_columns if col in a_to_s or col == "fp"]

  settings_form = MapSettingsForm(request.GET)

  if request.GET:
    regions_form = RegionsForm(request.GET)

    filter_form = ShowcaseFilterForm(
      request.GET,
      initial={
        "hazard": "earthquake",
        "column": ["fp"],
      },
    )
    filter_form.full_clean()

    hazard = filter_form.cleaned_data.get("hazard", None)
    hazard_key = hazard.key if hazard else "earthquake_flood"
    column = filter_form.cleaned_data.get("column", "A")
  else:
    regions_form = RegionsForm(initial={"countries": ["ALL"], "areas": list()})
    filter_form = ShowcaseFilterForm(
      initial={
        "hazard": "earthquake",
        "column": ["fp"],
      },
    )
    hazard_key = "earthquake"
    column = "fp"

  countries_root = regions_form.create_countries_hierarchy(displayed_countries)

  return render(
    request,
    template,
    {
      "latitude": DEFAULT_LATITUDE,
      "longitude": DEFAULT_LONGITUDE,
      "countries": [countries_root],
      "hazard": hazard_key,
      "column": column,
      "table_columns": table_columns,
      "settings_form": settings_form,
      "displayed_countries": displayed_countries,
      "filter_form": filter_form,
    },
  )


@require_GET
def showcase_details(request):
  template = "showcase/showcase_details.html"

  hazard = request.GET.get("hazard")
  exposure = request.GET.get("column")

  return render(
    request,
    template,
    {
      "hazard": hazard,
      "exposure": exposure,
    },
  )
