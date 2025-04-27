from django.apps import AppConfig


class ShowcaseConfig(AppConfig):
  name = "showcase"
  verbose_name = "Multi-Hazard Scenario Showcase"
  nav_name = "Scenario showcase"
  description = "Showcase of multi-hazard event modelling in the Danube and La Palma"
  icon = "easel"
  myriad = True
