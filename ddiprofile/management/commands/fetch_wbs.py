import pandas as pd
import numpy as np # <-- add this import
from ddiprofile.models import WBSInformation
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Fetch WBS data from an Excel file and save it to the database'

    def handle(self, *args, **options):
        addMthYear = 'JUN2025'
        delMthYear = 'JUN2025'
        sheetname = 'wk2_data'

        deleted_count, _ = WBSInformation.objects.filter(monthyear=delMthYear).delete()
        print(f"Deleted {deleted_count} existing rows with monthyear = {delMthYear}")

        df = pd.read_excel(r"C:\Users\mclark80\Downloads\CATSExports\06_CATSReport_2025.xlsx", sheet_name=sheetname)

        for _, row in df.iterrows():
            workdescription_raw = row['Work Description']
            # Check for NaN, None, empty, or "NOT REQUIRED"
            if pd.isna(workdescription_raw):
                continue
            workdescription = str(workdescription_raw).strip()
            if not workdescription or workdescription.upper() == "NOT REQUIRED":
                continue  # skip blanks and "NOT REQUIRED"

            WBSInformation.objects.create(
                employee_id=row['PersNo'],
                employee_name=row['Empl/applname'],
                workdate=row['Workdate'],
                effort=row['Effort'],
                atype=row['A/Atype'],
                atypetext=row['AttAbsTxt'],
                wbs=row['Receiver WBS element'],
                description=row['Receiver WBS description'],
                initiative=row['Initiative'],
                workcategory=row['Work Category'],
                workdescription=workdescription,
                module=row['Module'],
                backlog=row['Backlog'],
                monthyear=addMthYear,
                wbstype=row['CAP or EXP'],
            )
            print(f"Date {row['Workdate']} | Name {row['Empl/applname']} saved.")