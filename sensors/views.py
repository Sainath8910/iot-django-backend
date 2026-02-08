from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SensorReading,UserProfile,Device,CropRecommendation
from django.core.mail import send_mail
from twilio.rest import Client
from django.conf import settings
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .forms import CustomUserCreationForm,EmailOrUsernameLoginForm
import threading
from .ai_engine import predict_disease, predict_stress, agrotech_decision
from datetime import timedelta
from .forms import UserProfileForm

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
            Crop: {sensor_data.get('crop')}
            Temperature: {sensor_data.get('temperature')}
            Humidity: {sensor_data.get('humidity')}
            Soil_moisture: {sensor_data.get('soil_moisture')}
            pH: {sensor_data.get('ph')}
            Time: {sensor_data.get("timestamp")}
            Disease: {sensor_data.get("disease")} 
            Confidence: {sensor_data.get("confidence"):.2f}
            Stress Level: {sensor_data.get("stress")}
            Decision: {sensor_data.get("decision")}
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
            f"Crop:{sensor_data.get('crop')} "
            f"Temp:{sensor_data.get('temperature')} "
            f"Soil:{sensor_data.get('soil_moisture')} "
            f"pH:{sensor_data.get('ph')}"
            f"Time:{sensor_data.get('timestamp')}"
            f"Disease:{sensor_data.get('disease')} "
            f"Stress:{sensor_data.get('stress')} "
            f"Confidence:{sensor_data.get('confidence')} "
            f"Decision:{sensor_data.get('decision')} "
        ),
        from_=settings.TWILIO_PHONE_NUMBER,
        to=phone if phone.startswith("+") else "+91" + phone
    )

def send_alerts_async(sensor_data, user):
    try:
        print("Async alert started")
        send_alert_email(sensor_data, user)
        print("Email sent")
        #send_alert_sms(sensor_data, user)
        print("SMS sent")
    except Exception as e:
        print("Async alert failed:", e)

@csrf_exempt
def sensor_data_api(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        # Multipart form-data (IoT + image)
        data = request.POST
        files = request.FILES

        device_id = data.get("device_id")
        if not device_id:
            return JsonResponse({"error": "device_id is required"}, status=400)

        device = Device.objects.select_related("owner").get(device_id=device_id)

        # Sensor values
        temperature = float(data.get("temperature", 0))
        humidity = float(data.get("humidity", 0))
        soil_moisture = int(data.get("soil_moisture", 0))
        ph = float(data.get("ph", 7))

        # IoT timestamp
        sensor_timestamp = parse_datetime(data.get("timestamp"))

        # Image
        image = files.get("image")
        if not image:
            return JsonResponse({"error": "Leaf image is required"}, status=400)

        # Save temporary image for CNN
        temp_path = f"media/temp/{files.get("image")}_leaf.jpg"
        with open(temp_path, "wb+") as f:
            for chunk in image.chunks():
                f.write(chunk)

        # === AI FUSION ===
        crop, disease, confidence = predict_disease(temp_path)
        print(disease, confidence)

        stress = predict_stress(
            crop,
            temperature,
            humidity,
            soil_moisture,
            ph
        )

        decision = agrotech_decision(disease, stress)

        is_healthy = "healthy" in disease.lower()
        alert_required = (not is_healthy or stress == "HIGH")

        # Store in DB
        reading = SensorReading.objects.create(
            device=device,
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            ph=ph,
            sensor_timestamp=sensor_timestamp,
            image=image,
            disease=disease,
            stress_level=stress,
            decision=decision,
            alert=alert_required,
            crop=crop
        )

        # Send alerts
        if alert_required:
            threading.Thread(
                target=send_alerts_async,
                args=({
                    "crop": crop,
                    "temperature": temperature,
                    "humidity": humidity,
                    "soil_moisture": soil_moisture,
                    "ph": ph,
                    "disease": disease,
                    "confidence": confidence,
                    "stress": stress,
                    "decision": decision,
                    "timestamp": sensor_timestamp
                }, device.owner),
                daemon=True
            ).start()

        return JsonResponse({
            "status": "success",
            "disease": disease,
            "stress_level": stress,
            "decision": decision,
            "timestamp": sensor_timestamp
        }, status=200)

    except Device.DoesNotExist:
        return JsonResponse({"error": "Invalid device_id"}, status=404)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

@login_required
def dashboard(request):
    # get devices owned by logged-in user
    user_devices = Device.objects.filter(owner=request.user)

    # get latest readings ONLY from user's devices
    readings = (
        SensorReading.objects
        .filter(device__in=user_devices)
        .order_by('-created_at')[:20]
    )

    return render(request, 'dashboard.html', {'readings': readings})
@login_required
def latest_readings(request):
    user_devices = Device.objects.filter(owner=request.user)

    readings = (
        SensorReading.objects
        .filter(device__in=user_devices)
        .order_by("-created_at")[:20]
    )

    data = []
    for r in readings:
        data.append({
            "id": r.id,
            "time": r.sensor_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if r.sensor_timestamp else "",
            "temperature": r.temperature,
            "humidity": r.humidity,
            "soil": r.soil_moisture,
            "ph": r.ph,
            "alert": r.alert,

            # must match JS
            "disease": r.disease,
            "stress": r.stress_level,
            "decision": r.decision,
            "image": r.image.url if r.image else "",
            "device": r.device.device_id,
        })

    return JsonResponse(data, safe=False)

def analysis_page(request):
    return render(request, "recomendations.html")

def get_case(request, reading_id):
    try:
        r = SensorReading.objects.select_related("device").get(id=reading_id)

        rec = CropRecommendation.objects.filter(
            crop=r.crop,
            disease=r.disease,
            stress_level=r.stress_level
        ).first()
        if not rec:
            rec = CropRecommendation.objects.filter(
                crop="Any",
                disease="Healthy",
                stress_level=r.stress_level
            ).first()
        if not rec:
            rec = CropRecommendation.objects.filter(
                disease=r.disease,
                stress_level="Any"
            ).first()

        return JsonResponse({
            "id": r.id,
            "crop": r.crop,
            "device": r.device.device_id,
            "time": r.sensor_timestamp.strftime("%Y-%m-%d %H:%M"),
            "image": r.image.url if r.image else "",
            "disease": r.disease,
            "confidence": getattr(r, "confidence", 0.0),
            "stress": r.stress_level,
            "stress_score": 90 if r.stress_level == "HIGH" else 40 if r.stress_level == "MEDIUM" else 10,
            "decision": r.decision,
            "temperature": r.temperature,
            "humidity": r.humidity,
            "soil_moisture": r.soil_moisture,
            "ph": r.ph,

            "recommendation": {
                "condition": rec.condition if rec else "",
                "reason": rec.reason if rec else "",
                "treatment": rec.treatment if rec else "",
                "fertilizer": rec.fertilizer if rec else "",
                "spray": rec.spray if rec else "",
                "severity": rec.severity if rec else ""
            }
        })

    except SensorReading.DoesNotExist:
        return JsonResponse({"error": "Case not found"}, status=404)
def get_alert_objects(request):
    devices = Device.objects.filter(owner=request.user)
    readings = SensorReading.objects.filter(alert=True, device__in=devices)
    return render(request, 'alerts.html', {'readings': readings})

def sensors_tiles_view(request):
    # Get latest sensor reading
    devices = Device.objects.filter(owner=request.user)
    reading = SensorReading.objects.filter(device__in=devices).order_by("-created_at").first()

    return render(request, "sensors.html", {"reading": reading})

# ---- Graph API ----
def sensor_graph_api(request):
    metric = request.GET.get("metric")

    qs = (
        SensorReading.objects
        .filter(device__owner=request.user)
        .select_related("device")
        .order_by("created_at")
    )

    result = {}
    for r in qs:
        device_id = r.device.device_id
        result.setdefault(device_id, []).append({
            "time": r.sensor_timestamp.strftime("%H:%M"),
            "value": getattr(r, metric)
        })

    return JsonResponse(result)

@login_required
def profile_view(request):
    user = request.user

    # Ensure profile exists
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # User devices
    devices = Device.objects.filter(owner=user)

    # Sensor stats
    total_readings = SensorReading.objects.filter(device__owner=user).count()
    total_alerts = SensorReading.objects.filter(device__owner=user, alert=True).count()

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = UserProfileForm(instance=profile)

    context = {
        "profile": profile,
        "devices": devices,
        "total_readings": total_readings,
        "total_alerts": total_alerts,
        "form": form,
    }

    return render(request, "profile.html", context)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Device, SensorReading


# -------- Devices Tiles Page --------
@login_required
def devices_view(request):
    devices = Device.objects.filter(owner=request.user)
    return render(request, "devices.html", {
        "devices": devices
    })


# -------- Device Readings Page --------
@login_required
def device_detail_view(request, device_id):
    device = get_object_or_404(Device, device_id=device_id, owner=request.user)

    readings = (
        SensorReading.objects
        .filter(device=device)
        .order_by("-created_at")
    )

    return render(request, "device_detail.html", {
        "device": device,
        "readings": readings
    })
