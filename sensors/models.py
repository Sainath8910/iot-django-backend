from django.db import models
from django.contrib.auth.models import User

class SensorReading(models.Model):
    temperature = models.FloatField()
    humidity = models.FloatField()
    soil_moisture = models.IntegerField()
    ph = models.FloatField()
    alert = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reading at {self.created_at}"

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
