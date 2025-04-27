import os
import random
import string
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-" + str.join("", (random.choice(string.hexdigits) for _ in range(12)))
DEBUG = True
if SECRET_KEY.startswith("django-insecure") and not DEBUG:
  raise Exception("using insecure SECRET_KEY without DEBUG.")

ALLOWED_HOSTS = ["*"]

APP_NAME = "MYRIAD-EU Multi-Risk Toolkit Dashboard"

# Application definition

INSTALLED_APPS = [
  # django apps
  "django.contrib.admin",
  "django.contrib.auth",
  "django.contrib.contenttypes",
  "django.contrib.sessions",
  "django.contrib.messages",
  "django.contrib.staticfiles",
  # third-party apps
  "crispy_forms",
  "crispy_bootstrap5",
  "django_cotton",
  "django_htmx",
  "template_partials",
  "django_browser_reload",
  "ninja",
  # local
  "shared",
  "dashboard",
  "ui",
  "curve_explorer",
  "exposure_at_risk",
  "vulnerability_index_editor",
  "scenario_calculator",
  "showcase",
  "data",
]

MIDDLEWARE = [
  "django.middleware.security.SecurityMiddleware",
  "django.contrib.sessions.middleware.SessionMiddleware",
  "django.middleware.common.CommonMiddleware",
  "django.middleware.csrf.CsrfViewMiddleware",
  "django.contrib.auth.middleware.AuthenticationMiddleware",
  "django.contrib.messages.middleware.MessageMiddleware",
  "django.middleware.clickjacking.XFrameOptionsMiddleware",
  "django_htmx.middleware.HtmxMiddleware",
  "django.middleware.gzip.GZipMiddleware",
  "django_browser_reload.middleware.BrowserReloadMiddleware",
]

ROOT_URLCONF = "dashboard.urls"

TEMPLATES = [
  {
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
      "context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
      ],
    },
  },
]

WSGI_APPLICATION = "dashboard.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
  "default": {
    "ENGINE": "django.contrib.gis.db.backends.spatialite",
    "NAME": BASE_DIR / "db.sqlite3",
  }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
  {
    "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
  },
  {
    "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
  },
  {
    "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
  },
  {
    "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
  },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

STATICFILES_DIRS = [
  os.path.join(BASE_DIR, "build"),
  os.path.join(BASE_DIR, "shared/build"),
]

STATICFILES_FINDERS = [
  "django.contrib.staticfiles.finders.FileSystemFinder",
  "django.contrib.staticfiles.finders.AppDirectoriesFinder",
  "dashboard.finders.NpmStringFinder",
]

NPM_FILE_PATTERNS = {
  "@gnatih/leaflet.legend": ["src/leaflet.legend.css"],
  "@popperjs": ["core/dist/umd/popper.min.js"],
  "bootstrap-icons": ["bootstrap-icons.svg"],
  "bootstrap": ["dist/js/bootstrap.min.js"],
  "chart.js": ["dist/chart.umd.js"],
  "datatables.net-bs5": ["css/dataTables.bootstrap5.min.css"],
  "datatables.net-buttons-bs5": ["css/buttons.bootstrap5.min.css"],
  "htmx-ext-class-tools": ["class-tools.js"],
  "htmx.org": ["dist/htmx.min.js"],
  "jszip": ["dist/jszip.min.js"],
  "leaflet": ["dist/leaflet.css", "dist/images/*.png"],
  "@fontsource": ["barlow/*.css", "barlow/files/barlow*.*"],
  "georaster": ["dist/*.js"],
  "georaster-layer-for-leaflet": ["dist/**/*.min.js"],
}

# NPM_STATIC_FILES_PREFIX = "vendor"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_ROOT = os.path.join(BASE_DIR, "static")

STORAGES = {
  "default": {
    "BACKEND": "django.core.files.storage.FileSystemStorage",
  },
  "staticfiles": {
    "BACKEND": "dashboard.storage.ForgivingManifestStaticFilesStorage",
  },
}

X_FRAME_OPTIONS = "SAMEORIGIN"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

DEFAULT_SRID = 4326

RASTER_DATA_ROOT = os.path.join(BASE_DIR, "data_raster")

# TODO choose logical duration
API_CACHE_TIMEOUT = 10000
