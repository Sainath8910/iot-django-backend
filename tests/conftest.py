import pytest
from django.contrib.auth.models import User
from sensors.models import Device, SensorReading

@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pass123")

@pytest.fixture
def device(user):
    return Device.objects.create(device_id="1", owner=user)

@pytest.fixture
def reading(device):
    return SensorReading.objects.create(
        reading_id="abc123",
        device=device,
        temperature=25,
        humidity=60,
        soil_moisture=1,
        ph=7
    )