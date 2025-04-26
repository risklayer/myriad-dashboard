from django.apps import AppConfig


class ExposureAtRiskConfig(AppConfig):
  name = "exposure_at_risk"
  verbose_name = "Exposure at Risk Explorer"
  nav_name = "Exposure at risk"
  description = (
    "A tool for calculating the exposure at risk for different hazards in NUTS3 regions of Europe"
  )
  icon = "exposure"
  myriad = True
