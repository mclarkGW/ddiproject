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
    last_refreshed = LastRefreshed.objects.first()
    initiatives = Initiative.objects.all() \
        .prefetch_related(
            'change_requests'
            ) \
            .order_by('title')
    cr = ChangeRequest.objects.all() \
        .prefetch_related(
            'features',
            'features__user_stories' 
            ) \
            .order_by('title')
    

    context = {
        'initiatives': initiatives,
        'cr': cr,
        'last_refreshed': last_refreshed,
    }

    return render(request, 'dashboard.html', context)