from django.urls import path
from .views import sensor_data_api,dashboard,latest_readings

urlpatterns = [
    path('sensor-data/', sensor_data_api),
    path('', dashboard),
    path('latest/', latest_readings),
]
