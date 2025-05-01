import requests
import base64
from datetime import datetime
from django.core.management.base import BaseCommand
from ddiprofile.models import Iteration


# Azure DevOps settings
ORGANIZATION = 'payerportfolio'  # Replace with your Azure DevOps organization name
PROJECT = 'USHC_AMER_US_ADU_HSP_Ua3'  # Replace with your Azure DevOps project name
PAT = 'CByqSGDnGCIxr6qgEBSdxWspYW2Yuuvgq5cdqdlliShNDKYtOnE3JQQJ99BCACAAAAA85jZPAAASAZDO474U'  # Replace with your Azure DevOps PAT
API_VERSION = "7.0"
BASE_URL = f"https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_apis/wit/classificationnodes/iterations?$depth=3&api-version={API_VERSION}"

class Command(BaseCommand):
    help = "Fetch all iterations from Azure DevOps (project-wide) and store them in the database"

    def handle(self, *args, **kwargs):
        # Clear all records from the Iteration tables
        Iteration.objects.all().delete()

        iterations = self.fetch_all_iterations()
        if iterations:
            self.save_iterations_to_db(iterations)
            self.stdout.write(self.style.SUCCESS(f"Successfully fetched and saved {len(iterations)} iterations."))
        else:
            self.stdout.write(self.style.WARNING("No iterations found or failed to fetch iterations."))

    def fetch_all_iterations(self):
        """Fetch all iterations from Azure DevOps using Classification Nodes API"""
        auth_header = base64.b64encode(f":{PAT}".encode()).decode()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {auth_header}'
        }

        response = requests.get(BASE_URL, headers=headers)

        if response.status_code == 200:
            data = response.json()
            iterations = self.flatten_iterations(data)
            return iterations
        else:
            self.stdout.write(self.style.ERROR(f"Failed to fetch iterations: {response.status_code} - {response.text}"))
            return []

    def flatten_iterations(self, iteration_node):
        """Flatten nested iterations into a flat list"""
        iterations = []

        def traverse(node, parent_path=""):
            path = f"{parent_path}\\{node['name']}" if parent_path else node['name']
            if "attributes" in node:  # If it's an iteration node
                iterations.append({
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "path": path,
                    "attributes": node.get("attributes", {})
                })
            for child in node.get("children", []):
                traverse(child, path)

        traverse(iteration_node)
        return iterations

    def save_iterations_to_db(self, iterations):
        """Save iterations to the database"""
        for iteration in iterations:
            iteration_id = iteration.get("id")
            name = iteration.get("name")
            path = iteration.get("path")
            attributes = iteration.get("attributes", {})
            start_date = attributes.get("startDate")
            finish_date = attributes.get("finishDate")
            

            # Convert startDate and finishDate to datetime objects
            start_date = start_date and datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ").date()
            finish_date = finish_date and datetime.strptime(finish_date, "%Y-%m-%dT%H:%M:%SZ").date()

            # Update or create the iteration in the database
            iteration_obj, created = Iteration.objects.update_or_create(
                iteration_id=iteration_id,
                defaults={
                    "name": name,
                    "path": path,
                    "start_date": start_date,
                    "finish_date": finish_date,
                    "scriptupdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created new iteration: {name}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Updated existing iteration: {name}"))