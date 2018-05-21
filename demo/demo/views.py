from django.shortcuts import render
from picker.models import League


def home(request):
    leagues = League.objects.filter(is_pickable=True)
    return render(request, 'picker/home.html', {'leagues': leagues})
