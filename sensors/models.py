from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username
    
class Device(models.Model):
    device_id = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.device_id} → {self.owner.username}"

class SensorReading(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, null=True, blank=True)

    # Sensor data
    temperature = models.FloatField(default=0.0)
    humidity = models.FloatField(default=0.0)
    soil_moisture = models.IntegerField(default=0)
    ph = models.FloatField(default=7.0)

    # IoT timestamp
    sensor_timestamp = models.DateTimeField(null=True, blank=True)

    # Leaf image
    image = models.ImageField(upload_to="crop_images/", null=True, blank=True)

    # AI outputs
    disease = models.CharField(max_length=100, default="Unknown")
    crop = models.CharField(max_length=100, default="Unknown")
    stress_level = models.CharField(max_length=20, default="Unknown")
    decision = models.TextField(default="No AI analysis available")

    alert = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.sensor_timestamp:
            return f"{self.device} @ {self.sensor_timestamp}"
        return f"{self.device} @ {self.created_at}"

class CropRecommendation(models.Model):
    crop = models.CharField(max_length=50)
    disease = models.CharField(max_length=100)
    stress_level = models.CharField(max_length=20)

    # AI readable
    condition = models.CharField(max_length=100)

    # Farmer readable
    reason = models.TextField()
    treatment = models.TextField()
    fertilizer = models.TextField()
    spray = models.TextField()

    severity = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.crop} | {self.disease} | {self.stress_level}"
