from django.urls import path
from . import views
from .views import dashboard_view


urlpatterns = [
    path('', views.index, name='index'),
# URL for New Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
# URL for Iteration View
    path('iteration/', views.iteration_view, name='iteration'),

]