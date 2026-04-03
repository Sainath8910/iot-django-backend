import pytest
from sensors.models import SensorReading

@pytest.mark.django_db
def test_alert_filter(client, user, device):
    client.login(username="testuser", password="pass123")

    SensorReading.objects.create(
        reading_id="abc",
        device=device,
        alert=True
    )

    response = client.get("/alerts/")

    assert response.status_code == 200
    assert len(response.context["readings"]) == 1