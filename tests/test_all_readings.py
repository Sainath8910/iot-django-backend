import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_all_readings(client, user, device, reading):
    client.login(username="testuser", password="pass123")

    url = reverse("all_readings")
    response = client.get(url)

    assert response.status_code == 200
    assert len(response.context["readings"]) == 1