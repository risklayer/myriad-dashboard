from django.urls import path
from ninja import NinjaAPI, Swagger


class SwaggerInMyriad(Swagger):
  template = "api/api_reference.html"


api_v1 = NinjaAPI(urls_namespace="data", docs=SwaggerInMyriad())

api_v1.add_router("/values", "data.v1.values.router")
api_v1.add_router("/columns", "data.v1.columns.router")
api_v1.add_router("/areas", "data.v1.areas.router")
api_v1.add_router("/curves", "data.v1.curves.router")
api_v1.add_router("/hrsc", "data.v1.hrsc.router")

urlpatterns = [
  path("api/v1/", api_v1.urls),
]
