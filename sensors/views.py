from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SensorReading,UserProfile,Device
from django.core.mail import send_mail
from twilio.rest import Client
from django.conf import settings
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import CustomUserCreationForm,EmailOrUsernameLoginForm
import threading

def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()

            UserProfile.objects.create(
                user=user,
                phone=form.cleaned_data['phone']
            )
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()

    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    if request.method == "POST":
        form = EmailOrUsernameLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = EmailOrUsernameLoginForm()

    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def send_alert_email(sensor_data,user):
    send_mail(
        subject="🚨 IoT ALERT DETECTED",
        message=f"""
            Alert detected!
            Temperature: {sensor_data.get('temperature')}
            Humidity: {sensor_data.get('humidity')}
            Soil_moisture: {sensor_data.get('soil_moisture')}
            pH: {sensor_data.get('ph')}
            Time: {sensor_data.get(timezone.now())}
        """,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=False
    )

def send_alert_sms(sensor_data, user):
    phone = getattr(user.userprofile, "phone", None)
    if not phone:
        return

    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    client.messages.create(
        body=(
            f"ALERT! "
            f"Temp:{sensor_data.get('temperature')} "
            f"Soil:{sensor_data.get('soil_moisture')} "
            f"pH:{sensor_data.get('ph')}"
        ),
        from_=settings.TWILIO_PHONE_NUMBER,
        to=phone if phone.startswith("+") else "+91" + phone
    )

def send_alerts_async(sensor_data, user):
    try:
        send_alert_email(sensor_data, user)
        send_alert_sms(sensor_data, user)
    except Exception as e:
        print("Async alert failed:", e)
        
@csrf_exempt
def sensor_data_api(request):

    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode("utf-8"))
            device_id = data.get("device_id")
            if not device_id:
                return JsonResponse({"error": "device_id is required"}, status=400)
            device = Device.objects.select_related("owner").get(device_id=device_id)
            SensorReading.objects.create(
                temperature=data.get('temperature'),
                humidity=data.get('humidity'),
                soil_moisture=data.get('soil_moisture'),
                ph=data.get('ph'),
                alert=data.get('alert')
            )
            if data.get('alert'):
                threading.Thread(
                    target=send_alerts_async,
                    args=(data, device.owner),
                    daemon=True
                ).start()
            return JsonResponse({"status": "success"}, status=200)

        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=400
            )

    # 👇 THIS LINE IS CRITICAL
    return JsonResponse(
        {"error": "Only POST method allowed"},status=405)

@login_required(login_url='login')
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