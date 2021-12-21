from django.shortcuts import render
from picker.models import League


def home(request):
    leagues = League.objects.all()
    return render(request, 'picker/home.html', {'leagues': leagues})
