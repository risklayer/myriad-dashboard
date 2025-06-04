from django.shortcuts import render
from django.views.decorators.http import require_GET

# from shared.pin import PinType, append_pinned_items, get_pinned, get_pinned_keys
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
  # TODO check that column is valid
  table_columns = request.GET.getlist("table_columns") or None

  # # pinned = get_pinned(request, PinType.EXPOSURE)
  # # # pinned_keys = get_pinned_keys(pinned)
  # # # pinned = append_pinned_items(pinned, PinType.EXPOSURE)

  settings_form = MapSettingsForm(request.GET)

  if request.GET:
    regions_form = RegionsForm(request.GET)

    filter_form = ShowcaseFilterForm(
      request.GET,
      initial={
        "hazard": "EQ",
        "columnn": ["fp"],
      },
    )
    filter_form.full_clean()

    hazard = filter_form.cleaned_data.get("hazard", None)
    hazard_key = hazard.key if hazard else "EQ_flood"
    column = filter_form.cleaned_data.get("column", "A")
  else:
    regions_form = RegionsForm(initial={"countries": ["ALL"], "areas": list()})
    filter_form = ShowcaseFilterForm(
      initial={
        "hazard": "EQ",
        "columnn": ["fp"],
      },
    )
    hazard_key = "EQ"
    column = "fp"

  countries_root = regions_form.create_countries_hierarchy(displayed_countries)
  # if not column:
  #   column = "fp"

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
      # # "pinned": pinned,
      # # "pinned_keys": pinned_keys,
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

  # if not hazard or not exposure:
  #   return HttpResponseNotFound("Sorry I can't find the data you're looking for")
  # # pinned = get_pinned(request, PinType.EXPOSURE)
  # # # pinned_keys = get_pinned_keys(pinned)
  # # # pinned = append_pinned_items(pinned, PinType.EXPOSURE)

  return render(
    request,
    template,
    {
      "hazard": hazard,
      "exposure": exposure,
      # "key": key,
      # # "pinned": pinned,
      # # "pinned_keys": pinned_keys,
    },
  )


# @require_POST
# def refine_form(request):
#   template = "showcase/refine_form.html"

#   # # pinned = get_pinned(request, PinType.EXPOSURE)
#   # # # pinned_keys = get_pinned_keys(pinned)
#   # # # pinned = append_pinned_items(pinned, PinType.EXPOSURE)

#   # TODO verify column is valid
#   column = request.POST.get("column", None)

#   return render(
#     request,
#     template,
#     {
#       "column": column,
#       # # "pinned": pinned,
#       # # "pinned_keys": pinned_keys,
#     },
#   )
