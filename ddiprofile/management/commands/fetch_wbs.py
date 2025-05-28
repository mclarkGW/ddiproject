import pandas as pd
from ddiprofile.models import WBSInformation
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Fetch WBS data from an Excel file and save it to the database'

    def handle(self, *args, **options):
        addMthYear = 'MAY2025'  # MMMYYYY format
        delMthYear = 'MAY2025'  # MMMYYYY format
        sheetname = 'wk4_data'

        # Remove only items where monthyear matches delMthYear
        deleted_count, _ = WBSInformation.objects.filter(monthyear=delMthYear).delete()
        print(f"Deleted {deleted_count} existing rows with monthyear = {delMthYear}")

        # Load Excel
        df = pd.read_excel(r"C:\Users\mclark80\Downloads\CATSExports\05_CATSReport_2025.xlsx", sheet_name=sheetname)

        # Save each row where workdescription != "NOT REQUIRED"
        for _, row in df.iterrows():
            workdescription = str(row['Work Description']).strip()
            if workdescription.upper() == "NOT REQUIRED":
                continue  # Skip rows where workdescription is NOT REQUIRED

            WBSInformation.objects.create(
                employee_id=row['PersNo'],
                employee_name=row['Empl/applname'],
                workdate=row['Workdate'],
                effort=row['Effort'],
                atype=row['A/AType'],
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