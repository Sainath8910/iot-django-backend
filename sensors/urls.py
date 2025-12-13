from django.urls import path
from .views import sensor_data_api,dashboard

urlpatterns = [
    path('sensor-data/', sensor_data_api),
    path('dashboard/', dashboard),
]
