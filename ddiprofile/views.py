from django.db.models import Sum, F, FloatField, Count
from django.shortcuts import render, get_object_or_404, redirect
from .models import Initiative,ChangeRequest,LastRefreshed, Iteration, crEpic, crChangeRequest, crFeature, crUserStory,crTask, crLastRefreshed, WBSInformation
from datetime import datetime, date
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import JsonResponse
import requests
import base64
import json
from itertools import groupby
from collections import Counter, defaultdict


def index(request):
    return render(request, 'index.html')

# Home View
def home(request):
    return render(request, 'home.html')

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
    
# CR Dashboard View
def cr_dashboard_view(request):
    last_refreshed = crLastRefreshed.objects.first()

    # Build rollup: workdescription -> total effort
    wbs_effort_map = defaultdict(float)
    for wbs in WBSInformation.objects.values('workdescription', 'effort'):
        wd = wbs['workdescription']
        effort = wbs['effort'] or 0
        if wd:
            wbs_effort_map[wd] += float(effort)


    # Prefetch features and their user stories for optimized queries
    cr = crChangeRequest.objects.all() \
        .prefetch_related(
            'features',
            'features__user_stories',
            'features__user_stories__tasks'
        ) \
        .order_by('clientaccounts')

    for change_request in cr:
        # 1. Story Point Rollups
        total_planned = 0
        total_done = 0
        total_active = 0
        total_new = 0

        # 2. PI Start/End across all features (for CR)
        cr_pi_start = None
        cr_pi_end = None

        for feature in change_request.features.all():
            # 3. PI Start/End for Feature
            pi_start = None
            pi_end = None

            for user_story in feature.user_stories.all():
                # Story Points Rollup
                try:
                    storypoints = float(user_story.storypoints)
                except (ValueError, TypeError):
                    storypoints = 0

                state = getattr(user_story, "state", "").strip().lower()
                # Planned (all user stories)
                total_planned += storypoints * 8
                # Done/Active/New
                if state == "done":
                    total_done += storypoints
                elif state in ("ready", "in progress", "test", "blocked"):
                    total_active += storypoints
                elif state in ("new", "backlog"):
                    total_new += storypoints

                # PI Start/End per Feature
                iteration_path = getattr(user_story, "iterationpath", None)
                if iteration_path:
                    try:
                        iteration = Iteration.objects.get(path=iteration_path)
                        if not pi_start or (iteration.start_date and iteration.start_date < pi_start):
                            pi_start = iteration.start_date
                        if not pi_end or (iteration.finish_date and iteration.finish_date > pi_end):
                            pi_end = iteration.finish_date
                    except Iteration.DoesNotExist:
                        pass

            # Attach feature-level PI dates if you want them on the feature:
            feature.pi_start = pi_start
            feature.pi_end = pi_end

            # CR-level PI dates: accumulate across all features
            if pi_start:
                if not cr_pi_start or pi_start < cr_pi_start:
                    cr_pi_start = pi_start
            if pi_end:
                if not cr_pi_end or pi_end > cr_pi_end:
                    cr_pi_end = pi_end

        # Attach rollups to the CR
        change_request.total_planned = total_planned
        change_request.total_done = total_done
        change_request.total_active = total_active
        change_request.total_new = total_new
        change_request.pi_start = cr_pi_start
        change_request.pi_end = cr_pi_end
        change_request.total_sp = total_done + total_active + total_new  # Total story points (in "hours") as sum of all states

        # Progress percentage for progress bar
        if change_request.total_sp > 0:
            change_request.percent_done = int(round((change_request.total_done / change_request.total_sp) * 100))
        else:
            change_request.percent_done = 0

        # +/- Target Date calculation (CR level)
        target = getattr(change_request, 'targetdate', None)
        pi_end = cr_pi_end
        if target and pi_end:
            days_diff = (target - pi_end).days
            if days_diff > 0:
                change_request.target_vs_pi = f'+{days_diff}'
            elif days_diff < 0:
                change_request.target_vs_pi = f'{days_diff}'
            else:
                change_request.target_vs_pi = '0'
        else:
            change_request.target_vs_pi = ''

        # Attach WBS effort rollup to each CR using tt_workdescription
        workdesc = getattr(change_request, 'tt_workdescription', None)
        change_request.wbs_total_effort = wbs_effort_map.get(workdesc, 0)

        # --- TASK ROLLUPS ---
        total_originalestimate = 0.0
        total_remainingwork = 0.0
        total_completedwork = 0.0
        all_tasks = []

        for feature in change_request.features.all():
            for user_story in feature.user_stories.all():
                for task in user_story.tasks.all():
                    all_tasks.append(task)
                    # originalestimate
                    try:
                        total_originalestimate += float(task.originalestimate or 0)
                    except (ValueError, TypeError):
                        pass
                    # remainingwork
                    try:
                        total_remainingwork += float(task.remainingwork or 0)
                    except (ValueError, TypeError):
                        pass
                    # completedwork
                    try:
                        total_completedwork += float(task.completedwork or 0)
                    except (ValueError, TypeError):
                        pass

        change_request.tasks = all_tasks  # List of all tasks under this CR (for display)
        change_request.total_task_originalestimate = total_originalestimate
        change_request.total_task_remainingwork = total_remainingwork
        change_request.total_task_completedwork = total_completedwork

        # *** Planned vs Estimate Calculation ***
        highlevelestimate_raw = getattr(change_request, 'highlevelestimate', 0) or 0
        try:
            highlevelestimate = float(highlevelestimate_raw)
        except (ValueError, TypeError):
            highlevelestimate = 0
        change_request.planned_vs_estimate = change_request.total_task_originalestimate - highlevelestimate

    context = {
        'last_refreshed': last_refreshed,
        'cr': cr,
    }
    return render(request, 'crdashboard.html', context)

# CR Charts View
def cr_charts_view(request):
    crs = crChangeRequest.objects.prefetch_related('features', 'features__user_stories')

    # RELEASE aggregation (already correct)
    last_release_list = []
    for cr in crs:
        all_userstory_releases = []
        for feature in cr.features.all():
            for user_story in feature.user_stories.all():
                userstory_release = getattr(user_story, "iterationpath", None)
                if userstory_release:
                    if "\\" in userstory_release:
                        userstory_release = userstory_release.split("\\", 1)[1]
                    all_userstory_releases.append(userstory_release)
        last_release = max(all_userstory_releases) if all_userstory_releases else None
        last_release_list.append(last_release if last_release else '(blank)')
    release_counter = Counter(last_release_list)
    sorted_release_items = sorted(release_counter.items(), key=lambda x: x[0])
    release_labels = [item[0] for item in sorted_release_items]
    release_data = [item[1] for item in sorted_release_items]

    # ACCOUNT aggregation (fix here)
    account_list = []
    for cr in crs:
        account = getattr(cr, 'clientaccounts', None)
        account_list.append(account if account else '(blank)')
    account_counter = Counter(account_list)
    sorted_account_items = sorted(account_counter.items(), key=lambda x: (x[0] == '(blank)', x[0]))
    account_labels = [item[0] for item in sorted_account_items]
    account_data = [item[1] for item in sorted_account_items]

    # STATUS aggregation (custom order)
    status_order = [
        'Funnel', 'Reviewing', 'Analyzing', 'Backlog',
        'Committed', 'In Progress', 'BLOCKED', 'Done'
    ]
    order_map = {name.lower(): i for i, name in enumerate(status_order)}
    status_list = []
    for cr in crs:
        status = getattr(cr, 'state', None)
        status_list.append(status if status else '(blank)')
    status_counter = Counter(status_list)
    sorted_status_items = sorted(
        status_counter.items(),
        key=lambda x: order_map.get(str(x[0]).strip().lower(), len(order_map))
    )
    status_labels = [item[0] for item in sorted_status_items]
    status_data = [item[1] for item in sorted_status_items]

    context = {
        'release_labels': json.dumps(release_labels),
        'release_data': json.dumps(release_data),
        'account_labels': json.dumps(account_labels),
        'account_data': json.dumps(account_data),
        'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data),
    }
    return render(request, 'cr_charts.html', context)