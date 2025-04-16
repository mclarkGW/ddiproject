import base64
import requests
from django.core.management.base import BaseCommand
from datetime import datetime
from ddiprofile.models import Initiative, Epic, LastRefreshed  # Adjust according to your app structure

class Command(BaseCommand):
    help = 'Fetch Initiatives and Epics from Azure DevOps and store them in the database'

    def handle(self, *args, **kwargs):
        # Clear all records from the Initiative and Epic tables
        Initiative.objects.all().delete()
        Epic.objects.all().delete()

        organization = 'payerportfolio'
        project_initiatives = 'MES%20(Portfolio)'
        project_epics = 'USHC_AMER_US_ADU_HSP_Ua3'
        pat = 'CByqSGDnGCIxr6qgEBSdxWspYW2Yuuvgq5cdqdlliShNDKYtOnE3JQQJ99BCACAAAAA85jZPAAASAZDO474U'
        url_initiatives = f'https://dev.azure.com/{organization}/{project_initiatives}/_apis/wit/wiql?api-version=7.0'
        url_epics = f'https://dev.azure.com/{organization}/{project_epics}/_apis/wit/wiql?api-version=7.0'
        # ADO Id of the Parent Play to Initiative |Customer Value: 2584481
        playid = '2584481'

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


                for initiative_data in initiatives:
                    # Debugging: Log Initiative before saving
                    print(f"Saving Initiative: {initiative_data.get('title')} | Work Item ID: {initiative_data.get('id')}")

                    # Parse dates
                    parsed_start = parse_date(initiative_data.get('start'))
                    parsed_sitstart = parse_date(initiative_data.get('sitstart'))
                    parsed_uatstart = parse_date(initiative_data.get('uatstart'))
                    parsed_golivedate = parse_date(initiative_data.get('golivedate'))

                    # Update or create Initiative
                    defaults = {
                        'title': initiative_data.get('title'),
                        'workitemtype': initiative_data.get('workitemtype'),
                        'currentphase': initiative_data.get('currentphase'),
                        'golivedate': parsed_golivedate,
                        'months': parse_int(initiative_data.get('months')),
                        'sitcmpl': parse_float(initiative_data.get('sitcmpl')),
                        'sitstart': parsed_sitstart,
                        'start': parsed_start,
                        'uatcmpl': parse_float(initiative_data.get('uatcmpl')),
                        'uatstart': parsed_uatstart,
                    }

                    initiative, created = Initiative.objects.update_or_create(
                        id=initiative_data.get('id'),
                        defaults=defaults
                    )

                    epic_query_payload = {
                        "query": f"""
                        SELECT [System.Id]
                        FROM WorkItems
                        WHERE
                            [System.WorkItemType] = 'Epic'
                            AND [System.Parent] = {initiative_data.get('id')}
                            AND [System.State] NOT IN ('Obsolete', 'Duplicate', 'Cancelled', 'Archived')
                            AND [Custom.EpicCategory] IN ('CR', 'GAP')
                        ORDER BY [Custom.EpicCategory] ASC
                        """
                    }

                    epic_response = requests.post(url_epics, headers=headers, json=epic_query_payload)
                    epic_response.raise_for_status()  # Raise an exception for HTTP errors
                    epic_work_item_ids = [str(item['id']) for item in epic_response.json().get('workItems', [])]

                    if epic_work_item_ids:
                        epics = fetch_work_item_details(organization, project_epics, pat, epic_work_item_ids)

                        # Log all fetched Epic Categories for debugging
                        #print("Fetched Epic Categories:", [epic.get('epiccategory', '') for epic in epics])

                        # Normalize and filter epics to only include 'CR' or 'GAP'
                        epics = [
                            epic for epic in epics
                            if epic.get('epiccategory', '').strip().upper() in ['CR', 'GAP']
                        ]

                        # Debugging: Log filtered Epic Categories
                        #print("Filtered Epic Categories:", [epic.get('epiccategory') for epic in epics])


                        for epic_data in epics:
                            # Debugging: Log epiccategory before saving
                            print(f"Saving Epic: {epic_data.get('title')} | Work Item ID: {epic_data.get('id')} | Epic Category: {epic_data.get('epiccategory')}")

                            # Parse dates
                            parsed_requiredbdate = parse_date(epic_data.get('requiredbdate'))
                            parsed_enddate = parse_date(epic_data.get('enddate'))
                            parsed_created_date = parse_date(epic_data.get('created_date'))

                            # Update or create Epic
                            defaults = {
                                'title': epic_data.get('title'),
                                'workitemtype': epic_data.get('workitemtype'),
                                'state': epic_data.get('state') or 'Unknown',
                                'areapath': epic_data.get('areapath'),
                                'iterationpath': epic_data.get('iterationpath'),
                                'enddate': parsed_enddate,
                                'statuschoice': epic_data.get('statuschoice'),
                                'statustextbox': epic_data.get('statustextbox'),
                                'requiredbdate': parsed_requiredbdate,
                                'epiccategory': epic_data.get('epiccategory'),
                                'created_date': parsed_created_date,
                                'initiative': initiative,
                            }

                            Epic.objects.update_or_create(
                                id=epic_data.get('id'),
                                defaults=defaults
                            )

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Azure DevOps: {e}")

        # Update the LastRefreshed model
        now = datetime.now()
        LastRefreshed.objects.update_or_create(
            id=1,
            defaults={
                'title': now.strftime("%Y-%m-%d %H:%M:%S")
            }
        )

        print('Updated LastRefreshed model')

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
                    'start': fields.get('Custom.ddi_StartDate', '') if 'fields' in item else '',
                    'uatcmpl': fields.get('Custom.ddi_UATCmpl','') if 'fields' in item else '',
                    'uatstart': fields.get('Custom.ddi_UATStartDate', '') if 'fields' in item else '',
                    'statuschoice': fields.get('Custom.StatusChoice', '') if 'fields' in item else 'No Status Found',
                    'statustextbox': fields.get('Custom.StatusTextBox', '') if 'fields' in item else 'No Status Narrative Found',
                    'requiredbdate': fields.get('Custom.RequiredByDate', '') if 'fields' in item else '',
                    'epiccategory': fields.get('Custom.EpicCategory', '') if 'fields' in item else 'No Epic Category Found',
                    'created_date': fields.get('System.CreatedDate', '') if 'fields' in item else '',
                    'enddate': fields.get('Microsoft.VSTS.Scheduling.EndDate', '') if 'fields' in item else '',
                    'state': fields.get('System.State', '') if 'fields' in item else '',
                    'areapath': fields.get('System.AreaPath', '') if 'fields' in item else '',
                    'iterationpath': fields.get('System.IterationPath', '') if 'fields' in item else '',
                })

    return work_items