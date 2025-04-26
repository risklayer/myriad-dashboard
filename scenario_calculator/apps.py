from django.apps import AppConfig


class ScenarioCalculatorConfig(AppConfig):
  name = "scenario_calculator"
  verbose_name = "Multi-Hazard Scenario Calculator and DSS"
  nav_name = "Scenario calculator/DSS"
  description = "A tool for calculating the probability, or combined impact, of two hazard events in NUTS3 regions of Europe"
  icon = "calendar-range"
  myriad = True
