from django.db import models

class SensorReading(models.Model):
    temperature = models.FloatField()
    humidity = models.FloatField()
    soil_moisture = models.IntegerField()
    ph = models.FloatField()
    alert = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reading at {self.created_at}"
