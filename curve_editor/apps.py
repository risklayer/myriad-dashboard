from django.apps import AppConfig


class CurveEditorConfig(AppConfig):
  name = "curve_editor"
  verbose_name = "Vulnerability Curve Editor"
  description = "A tool for generating vulnerability curves for different hazards in Europe, for use with other MYRIAD-EU tools."
  icon = "graph-up"
  myriad = True
