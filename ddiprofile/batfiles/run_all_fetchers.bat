@echo off
REM Change directory to where your scripts are, if needed:
cd C:\Users\mclark80\PycharmProjects\ddiproject

REM Run each Django managment command in order
python manage.py fetch_data
python manage.py crfetch_data
python manage.py gapfetch_data
python manage.py fetch_iterationsALL

REM Pause to keep the window open (optional)
REM pause