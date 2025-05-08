from data.models import (
  Hazard,
  HrscScenario,
  HrscScenarioExposureVulnerabilityMapping,
  HrscExposure,
  VulnerabilityCurve,
  HrscEventCollection,
)
from django.core.management.base import BaseCommand

import json

from data.utils import clear_cache


class Command(BaseCommand):
  help = "Add a data set"

  def add_arguments(self, parser):
    parser.add_argument("filename", type=str)

  def handle(self, *args, filename: str, **options):
    scenarios = json.load(open(filename))

    for scenario_data in scenarios:
      scenario_instance = HrscScenario.get_or_create_by_label(
        slug_key=scenario_data["key"],
        label=scenario_data["label"],
        description=scenario_data["description"],
        hazard=Hazard.objects.get(key=scenario_data["hazard"]),
        event_collection=HrscEventCollection.objects.get(key=scenario_data["event_collection"]),
      )

      HrscScenarioExposureVulnerabilityMapping.objects.filter(scenario=scenario_instance).delete()

      for mapping_data in scenario_data["vulnerability_mapping"]:
        HrscScenarioExposureVulnerabilityMapping.objects.create(
          scenario=scenario_instance,
          exposure=HrscExposure.objects.get(key=mapping_data["exposure"]),
          vulnerability=VulnerabilityCurve.objects.get(
            key__icontains=mapping_data["vulnerability"]
          ),
        )

    print("Resetting cache")
    clear_cache()
    print("Done")
