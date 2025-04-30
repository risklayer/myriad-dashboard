from django import template
from django.urls import reverse
from django.apps import apps

register = template.Library()


def get_myriad_apps():
  myriad_apps = []
  for name, app in apps.app_configs.items():
    if getattr(app, "myriad", False):
      myriad_apps.append(
        {
          "name": app.verbose_name,
          "nav_name": getattr(app, "nav_name", app.verbose_name),
          "description": app.description,
          "icon": app.icon,
          "url": reverse(app.label + ":" + getattr(app, "home", "index")),
        }
      )
  return myriad_apps


@register.inclusion_tag("dashboard_header_apps.html", takes_context="True")
def dashboard_header_apps(context):
  return {
    "myriad_apps": get_myriad_apps(),
    "request": context.request,
  }


@register.inclusion_tag("dashboard_home_apps.html", takes_context="True")
def dashboard_home_apps(context, list_item_class: str = ""):
  return {
    "myriad_apps": get_myriad_apps(),
    "list_item_class": list_item_class,
    "request": context.request,
  }
