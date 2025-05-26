from django.shortcuts import render


def index(request):
  return render(request, "dashboard/index.html")


def glossary(request):
  return render(request, "dashboard/glossary.html")
