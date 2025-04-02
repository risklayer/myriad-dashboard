from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def index(request):
  template = "boilerplate/index.html"

  return render(
    request,
    template,
    {},
  )
