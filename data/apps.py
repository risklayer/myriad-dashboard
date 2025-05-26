from django.apps import AppConfig


class DataConfig(AppConfig):
  default_auto_field = "django.db.models.BigAutoField"
  name = "data"
  verbose_name = "Data API"
  nav_name = "API"
  description = (
    "OpenAPI data backend for accessing the data that underlies the tools in the tool set"
  )
  icon = "code"
  myriad = True
  home = "openapi-view"
