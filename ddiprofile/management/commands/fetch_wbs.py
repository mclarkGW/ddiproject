import pandas as pd
from ddiprofile.models import WBSInformation
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Fetch WBS data from an Excel file and save it to the database'

    def handle(self, *args, **options):
        addMthYear = 'MAY2025'  # MMMYYYY format
        delMthYear = 'MAY2025'  # MMMYYYY format

        # Remove only items where monthyear matches delMthYear
        deleted_count, _ = WBSInformation.objects.filter(monthyear=delMthYear).delete()
        print(f"Deleted {deleted_count} existing rows with monthyear = {delMthYear}")

        # Load Excel
        df = pd.read_excel(r"C:\Users\mclark80\Downloads\CATS_Report.xlsx", sheet_name="wk4_data")

        # Save each row where workdescription != "NOT REQUIRED"
        for _, row in df.iterrows():
            workdescription = str(row['workdescription']).strip()
            if workdescription.upper() == "NOT REQUIRED":
                continue  # Skip rows where workdescription is NOT REQUIRED

            WBSInformation.objects.create(
                employee_id=row['EID'],
                employee_name=row['Name'],
                workdate=row['Workdate'],
                effort=row['Effort'],
                atype=row['Atype'],
                atypetext=row['Atypetext'],
                wbs=row['wbs'],
                description=row['description'],
                initiative=row['initiative'],
                workcategory=row['workcategory'],
                workdescription=workdescription,
                module=row['module'],
                backlog=row['backlog'],
                wbstype=row['wbstype'],
                monthyear=addMthYear,
            )
            print(f"Date {row['Workdate']} | Name {row['Name']} saved.")