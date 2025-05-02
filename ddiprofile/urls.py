from django.urls import path
from . import views
from .views import dashboard_view


urlpatterns = [
    path('', views.index, name='index'),
# URL for New Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
# URL for Iteration View
    path('iteration/', views.iteration_view, name='iteration'),
# URL for New Dashboard 2
    path('dashboard2/', views.dashboard_view2, name='dashboard2'),
# URL for Fetch Iterations
    path('run-fetch-iterations/', views.run_fetch_iterations, name='run_fetch_iterations'),
# URL for Fetch Data
    path('run-fetch-data/', views.run_fetch_data, name='run_fetch_data'),
]