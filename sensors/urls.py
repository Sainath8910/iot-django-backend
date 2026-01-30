from django.urls import path
from .views import get_case, sensor_data_api,dashboard,latest_readings,register_view,login_view,logout_view,analysis_page

urlpatterns = [
    path('sensor-data/', sensor_data_api),
    path('', dashboard, name='dashboard'),
    path('latest/', latest_readings),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path("analysis/", analysis_page, name="analysis_page"),
    path("case/<int:reading_id>/", get_case),
]
