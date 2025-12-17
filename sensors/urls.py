from django.urls import path
from .views import sensor_data_api,dashboard,latest_readings,register_view,login_view,logout_view

urlpatterns = [
    path('sensor-data/', sensor_data_api),
    path('', dashboard, name='dashboard'),
    path('latest/', latest_readings),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
]
