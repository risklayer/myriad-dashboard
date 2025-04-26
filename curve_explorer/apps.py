from django.apps import AppConfig


class CurveExplorerConfig(AppConfig):
  name = "curve_explorer"
  verbose_name = "Vulnerability Curve Explorer"
  nav_name = "Multi-vuln. explorer"
  description = "A tool for finding and exporting vulnerability curves for different hazards in Europe, for use with other MYRIAD-EU tools"
  icon = "graph-up"
  myriad = True
