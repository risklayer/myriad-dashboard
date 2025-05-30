from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def index(request):
  template = "mrr_observatory/index.html"

  return render(
    request,
    template,
    {},
  )
