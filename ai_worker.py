import requests
import time
import os
from django.utils.dateparse import parse_datetime
from django.core.files import File
import django
import sys

sys.path.append(".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iot_backend.settings")
django.setup()

from sensors.models import SensorReading, Device
from sensors.ai_engine import predict_disease, predict_stress, agrotech_decision


COLLECTOR_URL = "https://iot-simulation-jl3f.onrender.com/get-unprocessed/"
UPDATE_URL = "https://iot-simulation-jl3f.onrender.com/update-result/"


def download_image(url, reading_id):
    filename = f"temp_{reading_id}.jpg"

    r = requests.get(url)

    if r.status_code != 200:
        raise Exception(f"Failed to download image: {url}")

    with open(filename, "wb") as f:
        f.write(r.content)

    return filename


def process():
    try:
        res = requests.get(COLLECTOR_URL)
        data = res.json().get("data", [])

        if not data:
            print("No data")
            return

        for item in data:
            print("Processing:", item["reading_id"])

            # Download image
            img_path = download_image(item["image_url"], item["reading_id"])

            # AI
            crop, disease, confidence = predict_disease(img_path)

            stress = predict_stress(
                crop,
                float(item["temperature"]),
                float(item["humidity"]),
                int(item["soil_moisture"]),
                float(item["ph"])
            )

            decision = agrotech_decision(disease, stress)

            # Save locally (optional)
            device, _ = Device.objects.get_or_create(device_id=item["device_id"])

            with open(img_path, "rb") as f:
                django_file = File(f)

                SensorReading.objects.create(
                    reading_id=item["reading_id"],
                    device=device,
                    temperature=item["temperature"],
                    humidity=item["humidity"],
                    soil_moisture=item["soil_moisture"],
                    ph=item["ph"],
                    sensor_timestamp=parse_datetime(item["timestamp"]),
                    image=django_file,   # ✅ THIS IS THE FIX
                    disease=disease,
                    stress_level=stress,
                    decision=decision,
                    crop=crop
                )

            # Send back to collector
            requests.post(
                UPDATE_URL,
                json={
                    "reading_id": item["reading_id"],
                    "disease": disease,
                    "stress": stress,
                    "decision": decision
                }
            )

            os.remove(img_path)

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    while True:
        process()
        time.sleep(5)