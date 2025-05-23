from django.urls import path
from . import views
from .views import dashboard_view


urlpatterns = [
    path('', views.index, name='index'),
# URL for DDI Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
# URL for Iteration View
    path('iteration/', views.iteration_view, name='iteration'),
# URL for Fetch Iterations
    path('run-fetch-iterations/', views.run_fetch_iterations, name='run_fetch_iterations'),
# URL for Fetch Data
    path('run-fetch-data/', views.run_fetch_data, name='run_fetch_data'),
# URL for CR Dashboard
    path('crdashboard/', views.cr_dashboard_view, name='crdashboard'),
]