import pytest

@pytest.mark.django_db
def test_latest_readings_api(client, user, device, reading):
    client.login(username="testuser", password="pass123")

    response = client.get("/latest/")

    assert response.status_code == 200
    data = response.json()

    assert len(data) >= 1
    assert data[0]["temperature"] == 25