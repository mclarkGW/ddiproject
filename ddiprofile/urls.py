from django.urls import path
from . import views
from .views import dashboard_view, cr_charts_view, gap_charts_view, export_ddi_dashboard, export_cr_dashboard, export_gap_dashboard


urlpatterns = [
    path('', views.index, name='index'),
# URL for DDI Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/export/', views.export_ddi_dashboard, name='ddi_export_excel'),
# URL for Iteration View
    path('iteration/', views.iteration_view, name='iteration'),
# URL for Fetch Iterations
    path('run-fetch-iterations/', views.run_fetch_iterations, name='run_fetch_iterations'),
# URL for Fetch DDI Data
    path('run-fetch-data/', views.run_fetch_data, name='run_fetch_data'),
# URL for Fetch CR Data
    path('run-crfetch-data/', views.run_crfetch_data, name='run_crfetch_data'),
# URL for CR Dashboard
    path('crdashboard/', views.cr_dashboard_view, name='crdashboard'),
    path('crdashboard/export/', views.export_cr_dashboard, name='cr_export_excel'),
# URL for CR Charts
    path('crcharts/', cr_charts_view, name='crcharts'),
# URL for GAP Dashboard
    path('gapdashboard/', views.gap_dashboard_view, name='gapdashboard'),
    path('gapdashboard/export/', views.export_gap_dashboard, name='gap_export_excel'),
# URL for GAP Charts
    path('gapcharts/', gap_charts_view, name='gapcharts'),
]