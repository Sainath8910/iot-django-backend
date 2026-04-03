import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_dashboard(client, user, device, reading):
    client.login(username="testuser", password="pass123")

    url = reverse("dashboard")
    response = client.get(url)

    assert response.status_code == 200
    assert "readings" in response.context