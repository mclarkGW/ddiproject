from django.db.models import Sum, F, FloatField
from django.shortcuts import render, get_object_or_404, redirect
from .models import Initiative,ChangeRequest,LastRefreshed, Iteration
from datetime import datetime
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import JsonResponse
import requests
import base64
import json
from itertools import groupby


def index(request):
    return render(request, 'index.html')

# DDI Dashboard View
def dashboard_view(request):
    last_refreshed = LastRefreshed.objects.first()
    initiatives = Initiative.objects.all() \
        .prefetch_related(
            'change_requests'
            ) \
            .order_by('clientaccounts')
    
    # Annotate "Total_Planned" for each ChangeRequest
    cr = ChangeRequest.objects.all() \
        .prefetch_related('features', 'features__user_stories') \
        .annotate(
            total_planned=Sum(
                F('features__user_stories__storypoints') * 8,
                output_field=FloatField()
            )
        ) \
        .order_by('tt_workdescription')

    context = {
        'initiatives': initiatives,
        'cr': cr,
        'last_refreshed': last_refreshed,
    }

    return render(request, 'dashboard.html', context)

# Iteration View
def iteration_view(request):
    # Last Refresh Date
    iteration_last_refreshed = Iteration.objects.first()
    # Get all iterations ordered by path and name
    iterations = Iteration.objects.all().order_by('id')

    # Group iterations by release (Level 2)
    grouped_iterations = {}
    for iteration in iterations:
        # Split the path to extract the release level
        path_parts = iteration.path.split('\\')
        if len(path_parts) > 1:  # Ensure there is a second level (Release)
            release = path_parts[1]
        else:
            release = "Project Level"  # Default group for invalid paths

        if release not in grouped_iterations:
            grouped_iterations[release] = []
        grouped_iterations[release].append(iteration)

    context = {
        'iterations': grouped_iterations,
        'iteration_last_refreshed': iteration_last_refreshed,
    }
    return render(request, 'iteration.html', context)

# Fetch Iterations View
def run_fetch_iterations(request):
    if request.method == "POST":
        try:
            # Call the custom management command
            call_command('fetch_iterations')
            return JsonResponse({"status": "success", "message": "Iterations fetched successfully!"})
        except CommandError as e:
            return JsonResponse({"status": "error", "message": str(e)})
    else:
        # Render the HTML template for GET requests
        return render(request, "run_fetch_iterations.html")

# Fetch Data View
def run_fetch_data(request):
    if request.method == "POST":
        try:
            # Call the custom management command
            call_command('fetch_data')
            return JsonResponse({"status": "success", "message": "Updated Data fetched successfully!"})
        except CommandError as e:
            return JsonResponse({"status": "error", "message": str(e)})
    else:
        # Render the HTML template for GET requests
        return render(request, "run_fetch_data.html")