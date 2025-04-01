from django.apps import AppConfig


class ExposureAtRiskConfig(AppConfig):
  name = "exposure_at_risk"
  verbose_name = "Exposure at Risk Calculator"
  description = "A tool for calculating the exposure at risk for different hazards in NUTS3 regions of Europe"
  icon = "exposure"
  myriad = True
