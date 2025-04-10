from django.shortcuts import render, get_object_or_404, redirect
from .models import DDIProfile, DDIStatus, Initiative,Epic,LastRefreshed
from .forms import DDIProfileForm, DDIStatusForm
from datetime import datetime
import requests
import base64
import json


def index(request):
    return render(request, 'index.html')

# Create DDIProfile
def ddi_profile_view(request, pk=None):
    if pk:
        profile = get_object_or_404(DDIProfile, pk=pk)

    else:
        profile = None

    if request.method == 'POST':
        form = DDIProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('ddi_profile_list')

    else:
        form = DDIProfileForm(instance=profile)

    return render(request, 'ddi_profile_form.html', {'form': form})

# Create DDIStatus
def ddi_status_view(request, pk=None):
    # Retrieve the DDIStatus if pk exists, otherwise create a new one
    if pk:
        status = get_object_or_404(DDIStatus, pk=pk)
    else:
        status = None

    previous_url = request.POST.get('previous_url', request.META.get('HTTP_REFERER', '/'))

    if request.method == 'POST':
        form = DDIStatusForm(request.POST, instance=status)
        if form.is_valid():
            form.save()
            return redirect(previous_url)
    else:
        # Prepopulate the Name field with the associated Profile's Name if it exists
        if status and status.profile:
            profile_name = status.profile.name
        else:
            profile_name = request.GET.get('profile_name', '')

        form = DDIStatusForm(initial={'name': profile_name}, instance=status)

    return render(request, 'ddi_status_form.html', {'form': form, 'previous_url': previous_url})

# List all DDI Profiles
def ddi_profile_list(request):
    profiles = DDIProfile.objects.all()  # Fetch all DDIProfile objects
    return render(request, 'ddi_profile_list.html', {'profiles': profiles})

# List all DDI Status (Not Used)
def ddi_status_list(request):
    statuses = DDIStatus.objects.all()  # Fetch all DDIStatus objects
    return render(request, 'ddi_status_list.html', {'statuses': statuses})

# View to (Edit) specific DDIProfile and its associated DDIStatus
def ddi_profile_detail(request, pk):
    # Get the DDIProfile object by primary key (pk)
    profile = get_object_or_404(DDIProfile, pk=pk)

    # Fetch all DDIStatus objects related to the profile
    statuses = DDIStatus.objects.filter(name=profile).order_by('-date')

    # Handle the form submission for editing or creating a DDIProfile
    if request.method == 'POST':
        form = DDIProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('ddi_profile_detail', pk=profile.pk)  # Redirect to the same page after save
    else:
        form = DDIProfileForm(instance=profile)

    # Pass the profile, form, and associated statuses to the template
    return render(request, 'ddi_profile_detail.html', {
        'profile': profile,
        'statuses': statuses,
        'form': form,
    })

# View to (Show) specific DDIProfile and its associated DDIStatus
def ddi_profile_viewdetail(request, pk):
    # Get the DDIProfile object by primary key (pk)
    profile = get_object_or_404(DDIProfile, pk=pk)

    # Fetch all DDIStatus objects related to the profile
    statuses = DDIStatus.objects.filter(name=profile).order_by('-date')

    # Azure DevOps configuration
    organization = 'PayerPortfolio'
    project = 'USHC_AMER_US_ADU_HSP_Ua3'
    pat = 'CByqSGDnGCIxr6qgEBSdxWspYW2Yuuvgq5cdqdlliShNDKYtOnE3JQQJ99BCACAAAAA85jZPAAASAZDO474U'
    url = f'https://dev.azure.com/{organization}/{project}/_apis/wit/wiql?api-version=7.0'

    auth_header = base64.b64encode(f":{pat}".encode()).decode()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth_header}'
    }

    # Dynamically construct the WIQL query based on the state field of the DDIProfile
    state = profile.state
    #print(f'state: {state}')
    query_payload = {
        "query": f"""
        SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.AreaPath], [System.CreatedDate]
        FROM WorkItems
        WHERE [System.WorkItemType] = 'Epic' AND [Custom.ClientAccounts] CONTAINS '{state}' AND ([Custom.EpicCategory] = 'Strategic Roadmap - Investment' OR [Custom.EpicCategory] = 'Technical Roadmap - Investment')
        ORDER BY [System.CreatedDate] DESC
        """
    }

    try:
        response = requests.post(url, headers=headers, json=query_payload)
        work_items = []

        if response.status_code == 200:
            data = response.json()
            work_item_ids = [str(item['id']) for item in data.get('workItems', [])]
            print(f'Found work items: {work_item_ids}')

            if work_item_ids:
                # Fetch details of all matching work items in batches
                work_items = fetch_work_item_details(organization, project, pat, work_item_ids)
                print(f"Work items to be passed to template: {work_items}")

                # Convert date strings to datetime objects
                for item in work_items:
                    if 'requiredbydate' in item and item['requiredbydate'] != 'No Required By Date Found':
                        item['requiredbydate'] = datetime.strptime(item['requiredbydate'], '%Y-%m-%dT%H:%M:%SZ')
                    if 'enddate' in item and item['enddate'] != 'No End Date Found':
                        item['enddate'] = datetime.strptime(item['enddate'], '%Y-%m-%dT%H:%M:%SZ')

        else:
            print(f"Query request failed with status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        work_items = []
        print(f"Error fetching data from Azure DevOps: {e}")

    # Pass the profile, statuses, and work items to the template
    return render(request, 'ddi_profile_viewdetail.html', {'profile': profile, 'statuses': statuses, 'work_items': work_items})

# Function to fetch work item details in batches
def fetch_work_item_details(organization, project, pat, work_item_ids):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
    }
    work_items = []
    batch_size = 100  # Adjust batch size as needed

    for i in range(0, len(work_item_ids), batch_size):
        batch_ids = work_item_ids[i:i + batch_size]
        ids_string = ','.join(batch_ids)
        detail_url = f'https://dev.azure.com/{organization}/{project}/_apis/wit/workitems?ids={ids_string}&api-version=7.0'
        print(f"Detail request URL: {detail_url}")
        detail_response = requests.get(detail_url, headers=headers)

        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            for item in detail_data.get('value', []):
                fields = item.get('fields', {})
                work_items.append({
                    'id': item.get('id', 'No ID'),
                    'title': fields.get('System.Title', 'No Title Found'),
                    'workitemtype': fields.get('System.WorkItemType', 'No Work Item Type Found'),
                    'state': fields.get('System.State', 'No State Found'),
                    'created_date': fields.get('System.CreatedDate', 'No Created Date Found'),
                    'areapath': fields.get('System.AreaPath', 'No Area Path Found'),
                    'clientaccounts': fields.get('Custom.ClientAccounts', 'No Clients Found'),
                    'epiccategory': fields.get('Custom.EpicCategory', 'No Epic Category Found'),
                    'parentinitiative':fields.get('Custom.PARENTINITIATIVE', 'No Parent Initiative Found'),
                    'requiredbydate':fields.get('Custom.RequiredByDate', 'No Required By Date Found'),
                    'enddate':fields.get('Microsoft.VSTS.Scheduling.EndDate', 'No End Date Found'),
                    'status': fields.get('Custom.StatusChoice', 'No Status Found'),
                    'narrative': fields.get('Custom.StatusTextBox', 'No Narrative Found'),
                })
        else:
            print(f"Detail request failed with status code: {detail_response.status_code}")
            print(f"Response content: {detail_response.content}")

    return work_items

# View to (Show) ADO Initiatives and their child Epics
def ddi_dashboard(request):

    # Azure DevOps configuration
    organization = 'payerportfolio'
    project_initiatives = 'MES%20(Portfolio)'
    project_epics = 'USHC_AMER_US_ADU_HSP_Ua3'
    pat = 'CByqSGDnGCIxr6qgEBSdxWspYW2Yuuvgq5cdqdlliShNDKYtOnE3JQQJ99BCACAAAAA85jZPAAASAZDO474U'
    url_initiatives = f'https://dev.azure.com/{organization}/{project_initiatives}/_apis/wit/wiql?api-version=7.0'
    url_epics = f'https://dev.azure.com/{organization}/{project_epics}/_apis/wit/wiql?api-version=7.0'

    auth_header = base64.b64encode(f":{pat}".encode()).decode()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth_header}'
    }

    # Initialize work_items variable
    work_items = []

    # Step 1: Query for parent work items with title "Customer Value"
    parent_query_payload = {
        "query": """
        SELECT [System.Id]
        FROM WorkItems
        WHERE [System.Title] = 'Customer Value'
        """
    }

    try:
        parent_response = requests.post(url_initiatives, headers=headers, json=parent_query_payload)
        parent_work_item_ids = []

        if parent_response.status_code == 200:
            parent_data = parent_response.json()
            parent_work_item_ids = [str(item['id']) for item in parent_data.get('workItems', [])]

            if parent_work_item_ids:
                # Step 2: Query for child work items (Initiatives) of the parent work items
                child_query_payload = {
                    "query": f"""
                    SELECT [System.Id]
                    FROM WorkItems
                    WHERE
                        [System.WorkItemType] = 'Initiative'
                        AND [System.Parent] IN ({','.join(parent_work_item_ids)})
                    ORDER BY [System.Title] ASC
                    """
                }

                child_response = requests.post(url_initiatives, headers=headers, json=child_query_payload)
                work_items = []

                if child_response.status_code == 200:
                    child_data = child_response.json()
                    work_item_ids = [str(item['id']) for item in child_data.get('workItems', [])]

                    if work_item_ids:
                        # Fetch details of all matching work items in batches
                        work_items = fetch_work_item_details(organization, project_initiatives, pat, work_item_ids)

                        # Convert date strings to datetime objects
                        for item in work_items:
                            if 'golivedate' in item and item['golivedate'] != '':
                                item['golivedate'] = datetime.strptime(item['golivedate'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')
                            if 'sitstart' in item and item['sitstart'] != '':
                                item['sitstart'] = datetime.strptime(item['sitstart'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')
                            if 'start' in item and item['start'] != '':
                                item['start'] = datetime.strptime(item['start'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')
                            if 'uatstart' in item and item['uatstart'] != '':
                                item['uatstart'] = datetime.strptime(item['uatstart'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')

                        # Step 3: Fetch child Epics for each Initiative
                        for initiative in work_items:
                            initiative_id = initiative['id']
                            epic_query_payload = {
                                "query": f"""
                                SELECT
                                    [System.Id],
                                    [System.Title],
                                    [System.WorkItemType],
                                    [System.State],
                                    [System.AreaPath],
                                    [System.CreatedDate]
                                FROM WorkItems
                                WHERE
                                    [System.WorkItemType] = 'Epic'
                                    AND [System.Parent] = {initiative_id}
                                ORDER BY [System.Title] ASC
                                """
                            }
                            epic_response = requests.post(url_epics, headers=headers, json=epic_query_payload)

                            if epic_response.status_code == 200:
                                epic_data = epic_response.json()
                                epics = [{
                                    'id': item['id'],
                                    'title': item['fields']['System.Title'] if 'fields' in item and 'System.Title' in item['fields'] else 'No Title Found',
                                    'workitemtype': item['fields']['System.WorkItemType'] if 'fields' in item and 'System.WorkItemType' in item['fields'] else 'No Work Item Type Found',
                                    'state': item['fields']['System.State'] if 'fields' in item and 'System.State' in item['fields'] else 'No State Found',
                                    'areapath': item['fields']['System.AreaPath'] if 'fields' in item and 'System.AreaPath' in item['fields'] else 'No Area Path Found',
                                    'created_date': item['fields']['System.CreatedDate'] if 'fields' in item and 'System.CreatedDate' in item['fields'] else 'No Created Date Found'
                                } for item in epic_data.get('workItems', [])]

                                initiative['epics'] = epics

                else:
                    print(f"Child query request failed with status code: {child_response.status_code}")
                    print(f"Response content: {child_response.content}")

        else:
            print(f"Parent query request failed with status code: {parent_response.status_code}")
            print(f"Response content: {parent_response.content}")

    except requests.exceptions.RequestException as e:
        work_items = []
        print(f"Error fetching data from Azure DevOps: {e}")

    # Pass the work items to the template
    return render(request, 'ddi_dashboard.html', {'work_items': work_items})

# Function to fetch work item details in batches
def fetch_work_item_details(organization, project, pat, work_item_ids):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
    }
    work_items = []
    batch_size = 100  # Adjust batch size as needed

    for i in range(0, len(work_item_ids), batch_size):
        batch_ids = work_item_ids[i:i + batch_size]
        ids_string = ','.join(batch_ids)
        detail_url = f'https://dev.azure.com/{organization}/{project}/_apis/wit/workitems?ids={ids_string}&api-version=7.0'
        print(f"Detail request URL: {detail_url}")
        detail_response = requests.get(detail_url, headers=headers)

        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            for item in detail_data.get('value', []):
                fields = item.get('fields', {})
                work_items.append({
                    'id': item.get('id', 'No ID'),
                    'title': fields.get('System.Title', '') if 'fields' in item else 'No Title Found',
                    'workitemtype': fields.get('System.WorkItemType', '') if 'fields' in item else 'No Work Item Type Found',
                    'currentphase': fields.get('Custom.ddi_CurrentPhase', '') if 'fields' in item else 'No Current Phase Found',
                    'golivedate': fields.get('Custom.ddi_GoLiveDate', '') if 'fields' in item else '',
                    'months': fields.get('Custom.ddi_Months', '') if 'fields' in item else '',
                    'sitcmpl': fields.get('Custom.ddi_SITCmpl', '') if 'fields' in item else '',
                    'sitstart': fields.get('Custom.ddi_SITStartDate', '') if 'fields' in item else '',
                    'start': fields.get('Custom.ddi_StartDate', '') if 'fields' in item else '',
                    'uatcmpl': fields.get('Custom.ddi_UATCmpl','') if 'fields' in item else '',
                    'uatstart': fields.get('Custom.ddi_UATStartDate', '') if 'fields' in item else '',
                })
        else:
            print(f"Detail request failed with status code: {detail_response.status_code}")
            print(f"Response content: {detail_response.content}")

    return work_items

# DDI Dashboard View
def dashboard_view(request):
    initiatives = Initiative.objects.all().prefetch_related('epics').order_by('title')  # Sort Initiatives by title
    last_refreshed = LastRefreshed.objects.first()

    context = {
        'initiatives': initiatives,
        'last_refreshed': last_refreshed,
    }

    return render(request, 'dashboard.html', context)