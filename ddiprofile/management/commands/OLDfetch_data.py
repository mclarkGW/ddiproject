import base64
import os
import requests
from django.core.management.base import BaseCommand
from django.db.models import Q
from datetime import datetime
import pytz
from django.db import transaction
from ddiprofile.models import Initiative, ChangeRequest, Feature, UserStory, LastRefreshed

class Command(BaseCommand):
    help = 'Fetch Initiatives and Epics from Azure DevOps and store them in the database'

    def handle(self, *args, **kwargs):
        # Clear all records from the All tables
        Initiative.objects.all().delete()
        ChangeRequest.objects.all().delete()
        Feature.objects.all().delete()
        UserStory.objects.all().delete()

        organization = 'payerportfolio'
        project_initiatives = 'MES%20(Portfolio)'
        project_epics = 'USHC_AMER_US_ADU_HSP_Ua3'
        pat = 'CByqSGDnGCIxr6qgEBSdxWspYW2Yuuvgq5cdqdlliShNDKYtOnE3JQQJ99BCACAAAAA85jZPAAASAZDO474U'
        url_initiatives = f'https://dev.azure.com/{organization}/{project_initiatives}/_apis/wit/wiql?api-version=7.0'
        url_epics = f'https://dev.azure.com/{organization}/{project_epics}/_apis/wit/wiql?api-version=7.0'
        # ADO Id of the Parent Play to Initiative |Customer Value: 2584481
        playid = '2584481'
        testid = '2775737' # ADO Id of My Test Initiative MIKE CLARK TESTING

        auth_header = base64.b64encode(f":{pat}".encode()).decode()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {auth_header}'
        }

        child_query_payload = {
            "query": f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE
                [System.WorkItemType] = 'Initiative'
                AND [System.Parent] = {playid}
                AND [Custom.ddi_DashboardInclude] = 'YES'
            ORDER BY [System.Title] ASC
            """
        }

        try:
            child_response = requests.post(url_initiatives, headers=headers, json=child_query_payload)
            child_response.raise_for_status()  # Raise an exception for HTTP errors
            work_item_ids = [str(item['id']) for item in child_response.json().get('workItems', [])]

            if work_item_ids:
                initiatives = fetch_work_item_details(organization, project_initiatives, pat, work_item_ids)
                # Build a lookup for Initiatives by clientaccounts and solutiongotomarket
                initiative_lookup = {}
                for initiative_data in initiatives:
                    clientaccounts = initiative_data.get('clientaccounts', '').strip().upper()
                    solutiongotomarket = initiative_data.get('solutiongotomarket', '').strip().upper()
                    initiative_lookup.setdefault((clientaccounts, solutiongotomarket), []).append(initiative_data)

                for initiative_data in initiatives:
                    print(f"Saving Initiative: {initiative_data.get('title')} | Work Item ID: {initiative_data.get('id')}")                    
                    # Parse dates
                    parsed_start = parse_date(initiative_data.get('start'))
                    parsed_sitstart = parse_date(initiative_data.get('sitstart'))
                    parsed_uatstart = parse_date(initiative_data.get('uatstart'))
                    parsed_golivedate = parse_date(initiative_data.get('golivedate'))
                    parsed_sitend = parse_date(initiative_data.get('sitend'))
                    parsed_uatend = parse_date(initiative_data.get('uatend'))

                    defaults = {
                        'title': initiative_data.get('title'),
                        'workitemtype': initiative_data.get('workitemtype'),
                        'currentphase': initiative_data.get('currentphase'),
                        'golivedate': parsed_golivedate,
                        'months': parse_int(initiative_data.get('months')),
                        'sitcmpl': parse_float(initiative_data.get('sitcmpl')),
                        'sitstart': parsed_sitstart,
                        'sitend': parsed_sitend,
                        'start': parsed_start,
                        'uatcmpl': parse_float(initiative_data.get('uatcmpl')),
                        'uatstart': parsed_uatstart,
                        'uatend': parsed_uatend,
                        'clientaccounts': initiative_data.get('clientaccounts'),
                        'solutiongotomarket': initiative_data.get('solutiongotomarket'),
                        'deliverysupportleader': initiative_data.get('deliverysupportleader'),
                        'deliverysupportseniorleader': initiative_data.get('deliverysupportseniorleader'),
                        'deliverysupportdirector': initiative_data.get('deliverysupportdirector'),
                    }

                    initiative_obj, created = Initiative.objects.update_or_create(
                        id=initiative_data.get('id'),
                        defaults=defaults
                    )

                # Now, fetch all Change Requests and GAPs for all initiatives
                cr_query_payload = {
                    "query": f"""
                    SELECT [System.Id]
                    FROM WorkItems
                    WHERE
                        [System.WorkItemType] IN ('Change Request', 'GAP')
                        AND [System.State] NOT IN ('Cancelled','Duplicate','Obsolete')
                        AND [Custom.CID] NOT IN ('','NA','N/A')
                        AND [System.AreaPath] UNDER 'USHC_AMER_US_ADU_HSP_Ua3\\ART - Client'
                    ORDER BY [System.Title] ASC
                    """
                }

                cr_response = requests.post(url_epics, headers=headers, json=cr_query_payload)
                cr_response.raise_for_status()
                cr_work_item_ids = [str(item['id']) for item in cr_response.json().get('workItems', [])]

                if cr_work_item_ids:
                    changerequests = fetch_work_item_details(organization, project_epics, pat, cr_work_item_ids)

                    for changerequest_data in changerequests:
                        print(f"Saving {changerequest_data.get('workitemtype')}: {changerequest_data.get('title')} | Work Item ID: {changerequest_data.get('id')}")

                        # Parse dates
                        parsed_targetdate = parse_date(changerequest_data.get('targetdate'))
                        parsed_createddate = parse_date(changerequest_data.get('createddate'))
                        parsed_requiredbydate = parse_date(changerequest_data.get('requiredbydate'))

                        # Prepare defaults for ChangeRequest fields
                        defaults = {
                            'title': changerequest_data.get('title'),
                            'workitemtype': changerequest_data.get('workitemtype'),
                            'state': changerequest_data.get('state') or 'Unknown',
                            'areapath': changerequest_data.get('areapath'),
                            'iterationpath': changerequest_data.get('iterationpath'),
                            'clientaccounts': changerequest_data.get('clientaccounts'),
                            'solutiongotomarket': changerequest_data.get('solutiongotomarket'),
                            'targetdate': parsed_targetdate,
                            'highlevelestimate': changerequest_data.get('highlevelestimate'),
                            'tt_initiative': changerequest_data.get('tt_initiative'),
                            'tt_workdescription': changerequest_data.get('tt_workdescription'),
                            'tt_workcategory': changerequest_data.get('tt_workcategory'),
                            'tt_capwbs': changerequest_data.get('tt_capwbs'),
                            'tt_expwbs': changerequest_data.get('tt_expwbs'),
                            'tt_onshorewbs': changerequest_data.get('tt_onshorewbs'),
                            'tt_offshorewbs': changerequest_data.get('tt_offshorewbs'),
                            'createddate': parsed_createddate,
                            'requiredbydate': parsed_requiredbydate,
                        }

                        # Save or update ChangeRequest WITHOUT linking to initiatives yet
                        change_request_instance, created = ChangeRequest.objects.update_or_create(
                            id=changerequest_data.get('id'),
                            defaults=defaults
                        )
                        # Now, link to all relevant Initiatives (ManyToMany)
                        cr_client_accounts = [
                            acc.strip().upper() for acc in (changerequest_data.get('clientaccounts') or '').replace(',', ';').split(';') if acc.strip()
                        ]
                        cr_solution_goto_market = (changerequest_data.get('solutiongotomarket') or '').strip().upper()

                        # Find all initiatives that match any client account AND solutiongotomarket
                        q = Q()
                        for acc in cr_client_accounts:
                            # This will match if the Initiative's clientaccounts contains the account string
                            q |= Q(clientaccounts__icontains=acc)

                        initiatives_to_link = Initiative.objects.filter(
                            q,
                            solutiongotomarket__iexact=cr_solution_goto_market
                        )
                        change_request_instance.initiatives.set(initiatives_to_link)

                        # Query to fetch features related to the ChangeRequest/GAP
                        afeature_query_payload = {
                            "query": f"""
                            SELECT [System.Id]
                            FROM WorkItems
                            WHERE
                                [System.WorkItemType] = 'Feature'
                                AND [System.State] NOT IN ('Cancelled','Duplicate','Obsolete')
                                AND [System.AreaPath] NOT UNDER 'USHC_AMER_US_ADU_HSP_Ua3\\Team Archive - [DO NOT USE]'
                                AND [Custom.CID] = '{changerequest_data.get('tt_workdescription', '').strip().upper()}'
                            ORDER BY [System.Title] ASC
                            """
                        }

                        afeature_response = requests.post(url_epics, headers=headers, json=afeature_query_payload)
                        afeature_response.raise_for_status()  # Raise an exception for HTTP errors
                        afeature_work_item_ids = [str(item['id']) for item in afeature_response.json().get('workItems', [])]

                        if afeature_work_item_ids:
                            features = fetch_work_item_details(organization, project_epics, pat, afeature_work_item_ids)
                            for feature_data in features:
                                # Debugging: Log Feature Details before saving
                                print(f"Saving Feature: {feature_data.get('title')} | Work Item ID: {feature_data.get('id')}")
                                # Parse dates
                                parsed_targetdate = parse_date(feature_data.get('targetdate'))
                                parsed_startdate = parse_date(feature_data.get('startdate'))
                                parsed_createddate = parse_date(feature_data.get('createddate'))

                                # Update or create Feature
                                feature_defaults = {
                                    'title': feature_data.get('title'),
                                    'workitemtype': feature_data.get('workitemtype'),
                                    'state': feature_data.get('state') or 'Unknown',
                                    'areapath': feature_data.get('areapath'),
                                    'iterationpath': feature_data.get('iterationpath'),
                                    'clientaccounts':feature_data.get('clientaccounts'),
                                    'solutiongotomarket': feature_data.get('solutiongotomarket'),
                                    'targetdate': parsed_targetdate,
                                    'startdate': parsed_startdate,
                                    'highlevelestimate': feature_data.get('highlevelestimate'),
                                    'tt_initiative': feature_data.get('tt_initiative'),
                                    'tt_workdescription': feature_data.get('tt_workdescription'),
                                    'tt_workcategory': feature_data.get('tt_workcategory'),
                                    'tt_capwbs': feature_data.get('tt_capwbs'),
                                    'tt_expwbs': feature_data.get('tt_expwbs'),
                                    'tt_onshorewbs': feature_data.get('tt_onshorewbs'),
                                    'tt_offshorewbs': feature_data.get('tt_offshorewbs'),
                                    'createddate': parsed_createddate,
                                    'cr_related': change_request_instance,
                                }
                                feature_instance, created = Feature.objects.update_or_create(
                                    id=feature_data.get('id'),
                                    defaults=feature_defaults
                                )

                                # Fetch User Story children for the Feature
                                user_stories = fetch_user_story_children(organization, project_epics, pat,[feature_instance.id])
                                if user_stories:
                                    for user_story_data in user_stories:
                                        # Parse dates
                                        parsed_createddate = parse_date(user_story_data.get('createddate'))
                                        print(f"  Saving User Story: {user_story_data.get('id')} | {user_story_data.get('title')}")
                                        UserStory.objects.update_or_create(
                                            id=user_story_data.get('id'),
                                            defaults={
                                                'title': user_story_data.get('title'),
                                                'workitemtype': user_story_data.get('workitemtype'),
                                                'state': user_story_data.get('state'),
                                                'iterationpath': user_story_data.get('iterationpath'),
                                                'areapath': user_story_data.get('areapath'),
                                                'storypoints': user_story_data.get('storypoints'),
                                                'clientaccounts': user_story_data.get('clientaccounts'),
                                                'tt_initiative': user_story_data.get('tt_initiative'),
                                                'tt_workcategory': user_story_data.get('tt_workcategory'),
                                                'tt_workdescription': user_story_data.get('tt_workdescription'),
                                                'tt_capwbs': user_story_data.get('tt_capwbs'),
                                                'tt_expwbs': user_story_data.get('tt_expwbs'),
                                                'tt_onshorewbs': user_story_data.get('tt_onshorewbs'),
                                                'tt_offshorewbs': user_story_data.get('tt_offshorewbs'),
                                                'createddate': parsed_createddate,
                                                'feature_related': feature_instance
                                            }
                                        )

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Azure DevOps: {e}")

        # Update the LastRefreshed model
        now_utc = datetime.now(pytz.utc)
        eastern = pytz.timezone('US/Eastern')
        now = now_utc.astimezone(eastern)  # Convert to Eastern Time
        LastRefreshed.objects.update_or_create(
            id=1,
            defaults={
                'title': now.strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        # Retrieve the updated title from the model and log it
        last_refreshed = LastRefreshed.objects.get(id=1)
        self.stdout.write(f'Updated LastRefreshed model: {last_refreshed.title} EST')

# Function to parse date strings into datetime.date objects
def parse_date(date_str):
    if isinstance(date_str, datetime):
        return date_str.date()
    if date_str and isinstance(date_str, str):
        date_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',  # Format with fractional seconds
            '%Y-%m-%dT%H:%M:%SZ',     # Format without fractional seconds
            '%Y-%m-%dT%H:%M:%S',      # ISO 8601 format without timezone
            '%Y-%m-%d'                # Simple date format
        ]
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, date_format).date()
                return parsed_date
            except ValueError:
                continue
        return None
    return None

def parse_int(value):
    if value:
        try:
            return int(value)
        except ValueError:
            return None
    return None

def parse_float(value):
    if value:
        try:
            return float(value)
        except ValueError:
            return None
    return None

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
        detail_response = requests.get(detail_url, headers=headers)
        detail_response.raise_for_status()  # Raise an exception for HTTP errors

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
                    'sitend': fields.get('Custom.ddi_SITEndDate', '') if 'fields' in item else '',
                    'start': fields.get('Custom.ddi_StartDate', '') if 'fields' in item else '',
                    'uatcmpl': fields.get('Custom.ddi_UATCmpl','') if 'fields' in item else '',
                    'uatstart': fields.get('Custom.ddi_UATStartDate', '') if 'fields' in item else '',
                    'uatend': fields.get('Custom.ddi_UATEndDate', '') if 'fields' in item else '',
                    'statuschoice': fields.get('Custom.StatusChoice', '') if 'fields' in item else 'No Status Found',
                    'statustextbox': fields.get('Custom.StatusTextBox', '') if 'fields' in item else 'No Status Narrative Found',
                    'requiredbydate': fields.get('Custom.RequiredByDate', '') if 'fields' in item else '',
                    'epiccategory': fields.get('Custom.EpicCategory', '') if 'fields' in item else 'No Epic Category Found',
                    'createddate': fields.get('System.CreatedDate', '') if 'fields' in item else '',
                    'enddate': fields.get('Microsoft.VSTS.Scheduling.EndDate', '') if 'fields' in item else '',
                    'state': fields.get('System.State', '') if 'fields' in item else '',
                    'areapath': fields.get('System.AreaPath', '') if 'fields' in item else '',
                    'iterationpath': fields.get('System.IterationPath', '') if 'fields' in item else '',
                    'clientaccounts': fields.get('Custom.ClientAccounts', '') if 'fields' in item else '',
                    'solutiongotomarket': fields.get('Custom.SolutionGotoMarket', '') if 'fields' in item else '',
                    'targetdate': fields.get('Microsoft.VSTS.Scheduling.TargetDate', '') if 'fields' in item else '',
                    'startdate': fields.get('Microsoft.VSTS.Scheduling.StartDate', '') if 'fields' in item else '',
                    'highlevelestimate': fields.get('Custom.HighLevelEstimate', '') if 'fields' in item else '',
                    'tt_initiative': fields.get('Custom.TT_Initiative', '') if 'fields' in item else '',
                    'tt_workcategory': fields.get('Custom.TT_WorkCategory', '') if 'fields' in item else '',
                    'tt_workdescription': fields.get('Custom.CID', '') if 'fields' in item else '',
                    'tt_capwbs': fields.get('Custom.TT_CAPWBS', '') if 'fields' in item else '',
                    'tt_expwbs': fields.get('Custom.TT_EXPWBS', '') if 'fields' in item else '',
                    'tt_onshorewbs': fields.get('Custom.TT_OnShoreWBS', '') if 'fields' in item else '',
                    'tt_offshorewbs': fields.get('Custom.TT_OffShoreWBS', '') if 'fields' in item else '',
                    'storypoints': fields.get('Microsoft.VSTS.Scheduling.StoryPoints', '') if 'fields' in item else '',
                    'deliverysupportleader': fields.get('Custom.ddi_DeliverySupportLeader', '') if 'fields' in item else '',
                    'deliverysupportseniorleader': fields.get('Custom.ddi_DeliverySupportSeniorLeader', '') if 'fields' in item else '',
                    'deliverysupportdirector': fields.get('Custom.ddi_DeliverySupportDirector', '') if 'fields' in item else '',
                })

    return work_items

# NEW FUNCTION: Fetch only User Story children for a Feature
def fetch_user_story_children(organization, project, pat, feature_ids):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
    }
    user_story_ids = []
    batch_size = 100  # Adjust batch size as needed

    for i in range(0, len(feature_ids), batch_size):
        batch_ids = feature_ids[i:i + batch_size]
        ids_string = ','.join(map(str, batch_ids))  # Convert integers to strings
        detail_url = f'https://dev.azure.com/{organization}/{project}/_apis/wit/workitems?ids={ids_string}&$expand=relations&api-version=7.0'
        response = requests.get(detail_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        if response.status_code == 200:
            detail_data = response.json()
            for item in detail_data.get('value', []):
                # Check for "Child" relations
                relations = item.get('relations', [])
                for relation in relations:
                    if relation.get('rel') == 'System.LinkTypes.Hierarchy-Forward':  # "Child" link type
                        child_url = relation.get('url')
                        child_id = child_url.split('/')[-1]  # Extract the work item ID from the URL
                        user_story_ids.append(child_id)

    # Fetch details for all children and filter for User Stories
    user_stories = []
    if user_story_ids:
        user_story_details = fetch_work_item_details(organization, project, pat, user_story_ids)
        for child_data in user_story_details:
            if child_data.get('workitemtype') == 'User Story':  # Filter for User Stories
                user_stories.append(child_data)

    return user_stories