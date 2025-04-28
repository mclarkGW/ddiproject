from django.shortcuts import render, get_object_or_404, redirect
from .models import Initiative,ChangeRequest,LastRefreshed
from datetime import datetime
import requests
import base64
import json


def index(request):
    return render(request, 'index.html')


# DDI Dashboard View
def dashboard_view(request):
    initiatives = Initiative.objects.all().prefetch_related('change_requests').order_by('title')  # Sort Initiatives by title
    last_refreshed = LastRefreshed.objects.first()

    context = {
        'initiatives': initiatives,
        'last_refreshed': last_refreshed,
    }

    return render(request, 'dashboard.html', context)