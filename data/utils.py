from django.conf import settings
import numpy as np
from django.core.cache import caches


def calculate_azimuth(point1, point2):
  lat1, lon1 = point1
  lat2, lon2 = point2
  delta_lon = lon2 - lon1
  x = np.sin(np.radians(delta_lon)) * np.cos(np.radians(lat2))
  y = np.cos(np.radians(lat1)) * np.sin(np.radians(lat2)) - np.sin(np.radians(lat1)) * np.cos(
    np.radians(lat2)
  ) * np.cos(np.radians(delta_lon))
  azimuth = np.degrees(np.arctan2(x, y))
  return azimuth


def clear_cache():
  caches[settings.CACHE_MIDDLEWARE_ALIAS].clear()
