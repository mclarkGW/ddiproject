import base64
import os
import requests
import time
from django.core.management.base import BaseCommand
from datetime import datetime
import pytz
from django.db import transaction
from ddiprofile.models import crEpic, crFeature, crUserStory, crLastRefreshed, crChangeRequest, crTask

class Command(BaseCommand):
    help = 'Fetch Change Requests from Azure DevOps and store them in the database'

    def handle(self, *args, **kwargs):
        start_time = time.time()
        CUTOFF_DATE = datetime(2025, 1, 15).date()
        organization = 'payerportfolio'
        project_workitems = 'USHC_AMER_US_ADU_HSP_Ua3'
        pat = 'CByqSGDnGCIxr6qgEBSdxWspYW2Yuuvgq5cdqdlliShNDKYtOnE3JQQJ99BCACAAAAA85jZPAAASAZDO474U'
        url_workitems = f'https://dev.azure.com/{organization}/{project_workitems}/_apis/wit/wiql?api-version=7.0'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
        }

        cr_query_payload = {
            "query": f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE
                [System.WorkItemType] = 'Change Request'
                AND [System.State] NOT IN ('Cancelled','Duplicate','Obsolete')
                AND [Custom.CID] NOT IN ('','NA','N/A')
                AND [System.AreaPath] UNDER 'USHC_AMER_US_ADU_HSP_Ua3\\ART - Client'
            ORDER BY [System.Title] ASC
            """
        }

        # Track seen IDs for pruning
        seen_cr_ids = set()
        seen_feature_ids = set()
        seen_userstory_ids = set()
        seen_task_ids = set()

        try:
            cr_response = requests.post(url_workitems, headers=headers, json=cr_query_payload)
            cr_response.raise_for_status()
            work_item_ids = [str(item['id']) for item in cr_response.json().get('workItems', [])]

            if work_item_ids:
                changerequests = fetch_work_item_details(organization, project_workitems, pat, work_item_ids)

                with transaction.atomic():
                    for changerequest_data in changerequests:
                        # Filter: Only include CRs where if State is Done, TargetDate > 1/15/2025
                        if changerequest_data.get('state') == "Done":
                            target_date = parse_date(changerequest_data.get('targetdate'))
                            if not target_date or target_date <= CUTOFF_DATE:
                                print(
                                    f"Skipping Change Request ID {changerequest_data.get('id')} because State is 'Done' and TargetDate is not after 1/15/2025"
                                )
                                continue

                        defaults = {
                            'title': changerequest_data.get('title'),
                            'workitemtype': changerequest_data.get('workitemtype'),
                            'state': changerequest_data.get('state') or 'Unknown',
                            'targetdate': parse_date(changerequest_data.get('targetdate')),
                            'areapath': changerequest_data.get('areapath'),
                            'iterationpath': changerequest_data.get('iterationpath'),
                            'clientaccounts': changerequest_data.get('clientaccounts'),
                            'highlevelestimate': parse_float(changerequest_data.get('highlevelestimate')),
                            'tt_initiative': changerequest_data.get('tt_initiative'),
                            'tt_workcategory': changerequest_data.get('tt_workcategory'),
                            'tt_workdescription': changerequest_data.get('tt_workdescription'),
                            'tt_capwbs': changerequest_data.get('tt_capwbs'),
                            'tt_expwbs': changerequest_data.get('tt_expwbs'),
                            'tt_onshorewbs': changerequest_data.get('tt_onshorewbs'),
                            'tt_offshorewbs': changerequest_data.get('tt_offshorewbs'),
                            'epicnumber': changerequest_data.get('epicnumber'),
                        }
                        change_request_instance, created = crChangeRequest.objects.update_or_create(
                            id=changerequest_data.get('id'),
                            defaults=defaults
                        )
                        seen_cr_ids.add(change_request_instance.id)
                        print(f"Saving Change Request: {changerequest_data.get('id')} | {changerequest_data.get('title')}")

                        # Query associated Features
                        tt_workdescription = changerequest_data.get('tt_workdescription')
                        if not tt_workdescription:
                            print(
                                f"Skipping Feature Query for Change Request ID {changerequest_data.get('id')} due to missing tt_workdescription")
                            continue

                        feature_query_payload = {
                            "query": f"""
                            SELECT [System.Id]
                            FROM WorkItems
                            WHERE
                                [System.WorkItemType] = 'Feature'
                                AND [Custom.CID] = '{changerequest_data.get('tt_workdescription')}'
                            ORDER BY [System.Title] ASC
                            """
                        }

                        feature_response = requests.post(url_workitems, headers=headers, json=feature_query_payload)
                        feature_response.raise_for_status()
                        feature_work_items_ids = [str(item['id']) for item in feature_response.json().get('workItems', [])]

                        if feature_work_items_ids:
                            features = fetch_work_item_details(organization, project_workitems, pat, feature_work_items_ids)

                            for feature_data in features:
                                print(f" Saving Feature: {feature_data.get('id')} | {feature_data.get('title')}")
                                parsed_startdate = parse_date(feature_data.get('startdate'))
                                parsed_targetdate = parse_date(feature_data.get('targetdate'))
                                defaults = {
                                    'title': feature_data.get('title'),
                                    'workitemtype': feature_data.get('workitemtype'),
                                    'state': feature_data.get('state') or 'Unknown',
                                    'areapath': feature_data.get('areapath'),
                                    'iterationpath': feature_data.get('iterationpath'),
                                    'clientaccounts': feature_data.get('clientaccounts'),
                                    'startdate': parsed_startdate,
                                    'targetdate': parsed_targetdate,
                                    'highlevelestimate': parse_float(feature_data.get('highlevelestimate')),
                                    'tt_initiative': feature_data.get('tt_initiative'),
                                    'tt_workcategory': feature_data.get('tt_workcategory'),
                                    'tt_workdescription': feature_data.get('tt_workdescription'),
                                    'tt_capwbs': feature_data.get('tt_capwbs'),
                                    'tt_expwbs': feature_data.get('tt_expwbs'),
                                    'tt_onshorewbs': feature_data.get('tt_onshorewbs'),
                                    'tt_offshorewbs': feature_data.get('tt_offshorewbs'),
                                    'cr_related': change_request_instance
                                }
                                feature_instance, created = crFeature.objects.update_or_create(
                                    id=feature_data.get('id'),
                                    defaults=defaults
                                )
                                seen_feature_ids.add(feature_instance.id)

                                # --- Fetch and Save User Story Children (UPDATED CODE) ---
                                user_stories = fetch_user_story_children(organization, project_workitems, pat, [feature_instance.id])
                                if user_stories:
                                    for user_story_data in user_stories:
                                        print(f"  Saving User Story: {user_story_data.get('id')} | {user_story_data.get('title')}")
                                        user_story_instance, _ = crUserStory.objects.update_or_create(
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
                                                'feature_related': feature_instance
                                            }
                                        )
                                        seen_userstory_ids.add(user_story_instance.id)

                                        # Fetch and save child tasks for this User Story
                                        task_children = fetch_task_children(organization, project_workitems, pat, [user_story_instance.id])
                                        if task_children:
                                            for task_data in task_children:
                                                print(f"    Saving Task: {task_data.get('id')} | {task_data.get('title')}")
                                                task_instance, _ = crTask.objects.update_or_create(
                                                    id=task_data.get('id'),
                                                    defaults={
                                                        'title': task_data.get('title'),
                                                        'workitemtype': task_data.get('workitemtype'),
                                                        'state': task_data.get('state'),
                                                        'areapath': task_data.get('areapath'),
                                                        'iterationpath': task_data.get('iterationpath'),
                                                        'storypoints': task_data.get('storypoints'),
                                                        'originalestimate': task_data.get('originalestimate'),
                                                        'remainingwork': task_data.get('remainingwork'),
                                                        'completedwork': task_data.get('completedwork'),
                                                        'userstory_related': user_story_instance
                                                    }
                                                )
                                                seen_task_ids.add(task_instance.id)
                                # --------------------------------------------------------

        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching Change Requests: {e}")
            return

        # PRUNE: Delete any records not seen in this run
        crChangeRequest.objects.exclude(id__in=seen_cr_ids).delete()
        crFeature.objects.exclude(id__in=seen_feature_ids).delete()
        crUserStory.objects.exclude(id__in=seen_userstory_ids).delete()
        crTask.objects.exclude(id__in=seen_task_ids).delete()

        # Update the LastRefreshed model
        now_utc = datetime.now(pytz.utc)
        eastern = pytz.timezone('US/Eastern')
        now = now_utc.astimezone(eastern)
        crLastRefreshed.objects.update_or_create(
            id=1,
            defaults={
                'title': now_utc.strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        last_refreshed = crLastRefreshed.objects.get(id=1)
        end_time = time.time()
        duration = end_time - start_time
        mins, secs = divmod(duration, 60)
        self.stdout.write(f"Script duration: {int(mins)} min {secs:.2f} sec")
        self.stdout.write(f'Updated LastRefreshed model: {last_refreshed.title} EST')

# Add parse_date and fetch_work_item_details functions here, unchanged from your script.
def parse_date(date_str):
    if isinstance(date_str, datetime):
        return date_str.date()
    if date_str and isinstance(date_str, str):
        date_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d'
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

def fetch_work_item_details(organization, project, pat, work_item_ids):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
    }
    work_items = []
    batch_size = 100
    for i in range(0, len(work_item_ids), batch_size):
        batch_ids = work_item_ids[i:i + batch_size]
        ids_string = ','.join(batch_ids)
        detail_url = f'https://dev.azure.com/{organization}/{project}/_apis/wit/workitems?ids={ids_string}&api-version=7.0'
        detail_response = requests.get(detail_url, headers=headers)
        detail_response.raise_for_status()
        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            for item in detail_data.get('value', []):
                fields = item.get('fields', {})
                work_items.append({
                    'id': item.get('id', 'No ID'),
                    'title': fields.get('System.Title', '') if 'fields' in item else 'No Title Found',
                    'workitemtype': fields.get('System.WorkItemType', '') if 'fields' in item else 'No Work Item Type Found',
                    'state': fields.get('System.State', '') if 'fields' in item else '',
                    'areapath': fields.get('System.AreaPath', '') if 'fields' in item else '',
                    'iterationpath': fields.get('System.IterationPath', '') if 'fields' in item else '',
                    'clientaccounts': fields.get('Custom.ClientAccounts', '') if 'fields' in item else '',
                    'targetdate': fields.get('Microsoft.VSTS.Scheduling.TargetDate', '') if 'fields' in item else '',
                    'highlevelestimate': fields.get('Custom.HighLevelEstimate', '') if 'fields' in item else '',
                    'tt_initiative': fields.get('Custom.TT_Initiative', '') if 'fields' in item else '',
                    'tt_workcategory': fields.get('Custom.TT_WorkCategory', '') if 'fields' in item else '',
                    'tt_workdescription': fields.get('Custom.CID', '') if 'fields' in item else '',
                    'tt_capwbs': fields.get('Custom.TT_CAPWBS', '') if 'fields' in item else '',
                    'tt_expwbs': fields.get('Custom.TT_EXPWBS', '') if 'fields' in item else '',
                    'tt_onshorewbs': fields.get('Custom.TT_OnShoreWBS', '') if 'fields' in item else '',
                    'tt_offshorewbs': fields.get('Custom.TT_OffShoreWBS', '') if 'fields' in item else '',
                    'startdate': fields.get('Microsoft.VSTS.Scheduling.StartDate', '') if 'fields' in item else '',
                    'storypoints': fields.get('Microsoft.VSTS.Scheduling.StoryPoints', '') if 'fields' in item else '',
                    'originalestimate': fields.get('Microsoft.VSTS.Scheduling.OriginalEstimate', '') if 'fields' in item else '',
                    'remainingwork': fields.get('Microsoft.VSTS.Scheduling.RemainingWork', '') if 'fields' in item else '',
                    'completedwork': fields.get('Microsoft.VSTS.Scheduling.CompletedWork', '') if 'fields' in item else '',
                })
    return work_items

def fetch_user_story_children(organization, project, pat, feature_ids):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
    }
    user_story_ids = []
    batch_size = 100
    for i in range(0, len(feature_ids), batch_size):
        batch_ids = feature_ids[i:i + batch_size]
        ids_string = ','.join(map(str, batch_ids))
        detail_url = f'https://dev.azure.com/{organization}/{project}/_apis/wit/workitems?ids={ids_string}&$expand=relations&api-version=7.0'
        response = requests.get(detail_url, headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            detail_data = response.json()
            for item in detail_data.get('value', []):
                relations = item.get('relations', [])
                for relation in relations:
                    if relation.get('rel') == 'System.LinkTypes.Hierarchy-Forward':
                        child_url = relation.get('url')
                        child_id = child_url.split('/')[-1]
                        user_story_ids.append(child_id)
    user_stories = []
    if user_story_ids:
        user_story_details = fetch_work_item_details(organization, project, pat, user_story_ids)
        for child_data in user_story_details:
            if child_data.get('workitemtype') == 'User Story':
                user_stories.append(child_data)
    return user_stories

def fetch_task_children(organization, project, pat, user_story_ids):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
    }
    task_ids = []
    batch_size = 100
    for i in range(0, len(user_story_ids), batch_size):
        batch_ids = user_story_ids[i:i + batch_size]
        ids_string = ','.join(map(str, batch_ids))
        detail_url = f'https://dev.azure.com/{organization}/{project}/_apis/wit/workitems?ids={ids_string}&$expand=relations&api-version=7.0'
        response = requests.get(detail_url, headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            detail_data = response.json()
            for item in detail_data.get('value', []):
                relations = item.get('relations', [])
                for relation in relations:
                    if relation.get('rel') == 'System.LinkTypes.Hierarchy-Forward':
                        child_url = relation.get('url')
                        child_id = child_url.split('/')[-1]
                        task_ids.append(child_id)
    tasks = []
    if task_ids:
        task_details = fetch_work_item_details(organization, project, pat, task_ids)
        for child_data in task_details:
            if child_data.get('workitemtype') == 'Task':
                tasks.append(child_data)
    return tasks