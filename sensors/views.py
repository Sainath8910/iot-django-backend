from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SensorReading

@csrf_exempt
def sensor_data_api(request):

    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            SensorReading.objects.create(
                temperature=data.get('temperature'),
                humidity=data.get('humidity'),
                soil_moisture=data.get('soil_moisture'),
                ph=data.get('ph'),
                alert=data.get('alert')
            )

            return JsonResponse({"status": "success"}, status=200)

        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=400
            )

    # 👇 THIS LINE IS CRITICAL
    return JsonResponse(
        {"error": "Only POST method allowed"},
        status=405
    )

def dashboard(request):
    readings = SensorReading.objects.order_by('-created_at')[:20]
    return render(request, 'dashboard.html', {'readings': readings})