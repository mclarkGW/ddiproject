from django.urls import path
from . import views
from .views import dashboard_view


urlpatterns = [
    path('', views.index, name='index'),
    path('profile/', views.ddi_profile_view, name='ddi_profile_create'),
    path('profile/<int:pk>/', views.ddi_profile_view, name='ddi_profile_update'),
    path('status/', views.ddi_status_view, name='ddi_status_create'),
    path('status/<int:pk>/', views.ddi_status_view, name='ddi_status_update'),
# List views for DDIProfile and DDIStatus
    path('profiles/', views.ddi_profile_list, name='ddi_profile_list'),
    path('statuses/', views.ddi_status_list, name='ddi_status_list'),
# URL for the DDIProfile detail view
    path('profile/<int:pk>/detail/', views.ddi_profile_detail, name='ddi_profile_detail'),
    path('profile/<int:pk>/viewdetail/', views.ddi_profile_viewdetail, name='ddi_profile_viewdetail'),
# URL for Dashboard
    #path('dashboard/', views.ddi_dashboard, name='dashboard1'),
# URL for New Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),



]