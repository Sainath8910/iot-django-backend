from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SensorReading
from django.core.mail import send_mail
from twilio.rest import Client
from django.conf import settings


def send_alert_email(sensor_data):
    send_mail(
        subject="🚨 IoT ALERT DETECTED",
        message=f"""
Alert detected!

Temperature: {sensor_data.temperature}
Humidity: {sensor_data.humidity}
Soil: {sensor_data.soil}
pH: {sensor_data.ph}
Time: {sensor_data.timestamp}
        """,
        from_email='your_email@gmail.com',
        recipient_list=['admin@gmail.com'],
        fail_silently=False
    )

def send_alert_sms(sensor_data):
    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    client.messages.create(
        body=f"ALERT! Temp:{sensor_data.temperature} Soil:{sensor_data.soil} pH:{sensor_data.ph}",
        from_=settings.TWILIO_PHONE_NUMBER,
        to='+919490290489'
    )

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
            if data.alert:
                send_alert_email(data)
                send_alert_sms(data)
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

def latest_readings(request):
    readings = SensorReading.objects.order_by('-created_at')[:20]

    data = [
        {
            "time": r.created_at.strftime("%H:%M:%S"),
            "temperature": r.temperature,
            "humidity": r.humidity,
            "soil": r.soil_moisture,
            "ph": r.ph,
            "alert": r.alert
        }
        for r in readings[::-1]
    ]

    return JsonResponse(data, safe=False)