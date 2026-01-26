import os
import json
import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from django.conf import settings
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input

MODEL_DIR = os.path.join(settings.BASE_DIR, "model")

# Load CNN
cnn_model = tf.keras.models.load_model(
    os.path.join(MODEL_DIR, "agrotech_resnet50.h5")
)

with open(os.path.join(MODEL_DIR, "class_indices.json")) as f:
    class_map = json.load(f)
    class_map = {v:k for k,v in class_map.items()}

# Load Random Forest
stress_model = joblib.load(os.path.join(MODEL_DIR, "stress_model.pkl"))
crop_encoder = joblib.load(os.path.join(MODEL_DIR, "crop_encoder.pkl"))
stress_encoder = joblib.load(os.path.join(MODEL_DIR, "stress_encoder.pkl"))

def predict_disease(img_path):
    img = image.load_img(img_path, target_size=(224,224))
    img = image.img_to_array(img)

    # IMPORTANT: use ResNet50 preprocessing
    img = preprocess_input(img)

    img = np.expand_dims(img, axis=0)

    preds = cnn_model.predict(img)
    class_id = int(np.argmax(preds))
    disease = class_map[class_id]
    confidence = float(np.max(preds))

    return disease, confidence
def normalize_crop(crop):
    return str(crop).strip().title()

def predict_stress(crop, temp, humidity, moisture, ph):
    crop = normalize_crop(crop)

    crop_id = crop_encoder.transform([crop])[0]

    X = pd.DataFrame([{
        "crop_encoded": crop_id,
        "temperature_C": float(temp),
        "humidity_pct": float(humidity),
        "soil_moisture_pct": float(moisture),
        "soil_pH": float(ph)
    }])

    stress_id = stress_model.predict(X)[0]
    stress = stress_encoder.inverse_transform([stress_id])[0]

    return stress
def agrotech_decision(disease, confidence, stress):
    if disease != "Healthy" and stress == "High":
        return "CRITICAL: Disease will spread. Immediate treatment required."
    elif disease != "Healthy":
        return "WARNING: Disease detected. Monitor and apply treatment."
    elif stress == "High":
        return "PREVENTIVE: Crop under stress. Check irrigation and nutrients."
    else:
        return "Healthy. No action required."
