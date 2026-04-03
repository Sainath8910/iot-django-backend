import pytest
from unittest.mock import patch, MagicMock
from sensors.models import SensorReading
from wroker import process   # 👈 adjust import

@pytest.mark.django_db
@patch("wroker.requests.get")
@patch("wroker.requests.post")
@patch("wroker.download_image")
@patch("wroker.predict_disease")
@patch("wroker.predict_stress")
@patch("wroker.agrotech_decision")
def test_process_pipeline(
    mock_decision,
    mock_stress,
    mock_disease,
    mock_download,
    mock_post,
    mock_get,
    device
):

    # Fake collector response
    mock_get.return_value.json.return_value = {
        "data": [{
            "reading_id": "abc123",
            "device_id": "1",
            "temperature": 25,
            "humidity": 60,
            "soil_moisture": 1,
            "ph": 7,
            "timestamp": "2025-01-01T10:00:00Z",
            "image_url": "http://fake.com/img.jpg"
        }]
    }

    # Mock AI
    mock_disease.return_value = ("tomato", "healthy", 98.0)
    mock_stress.return_value = "LOW"
    mock_decision.return_value = "No action needed"

    # Mock image
    mock_download.return_value = "temp.jpg"

    with open("temp.jpg", "wb") as f:
        f.write(b"img")

    process()

    assert SensorReading.objects.count() == 1

    obj = SensorReading.objects.first()
    assert obj.disease == "healthy"

    mock_post.assert_called()   # update-result called