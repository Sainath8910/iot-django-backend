from django.urls import path
from .views import devices_view, device_detail_view,profile_view,get_alert_objects, get_case, sensor_data_api,dashboard,latest_readings,register_view,login_view,logout_view,analysis_page, sensor_graph_api, sensors_tiles_view

urlpatterns = [
    path('sensor-data/', sensor_data_api),
    path('', dashboard, name='dashboard'),
    path('latest/', latest_readings),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path("analysis/", analysis_page, name="analysis_page"),
    path("case/<int:reading_id>/", get_case),
    path('alerts/', get_alert_objects, name='alerts'),
    path("sensors/", sensors_tiles_view, name="sensors"),
    path("api/sensor-graph/", sensor_graph_api, name="sensor_graph_api"),
    path("profile/", profile_view, name="profile"),
    path("devices/", devices_view, name="devices"),
    path("devices/<str:device_id>/", device_detail_view, name="device_detail"),
]
