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

CLASS_MAP = {
    "Apple_Apple_scab": "Apple scab",
    "Apple_Black_rot": "Black rot",
    "Apple_Cedar_apple_rust": "Cedar apple rust",
    "Apple_healthy": "Healthy",

    "Blueberry_healthy": "Healthy",

    "Cherry_(including_sour)_healthy": "Healthy",
    "Cherry_(including_sour)_Powdery_mildew": "Powdery mildew",

    "Corn_(maize)_Cercospora_leaf_spot_Gray_leaf_spot": "Cercospora leaf spot / Gray leaf spot",
    "Corn_(maize)_Common_rust": "Common rust",
    "Corn_(maize)_Northern_Leaf_Blight": "Northern leaf blight",
    "Corn_(maize)_healthy": "Healthy",

    "Grape_Black_rot": "Black rot",
    "Grape_Esca_(Black_Measles)": "Esca (Black measles)",
    "Grape_Leaf_blight_(Isariopsis_Leaf_Spot)": "Leaf blight",
    "Grape_healthy": "Healthy",

    "Orange_Huanglongbing_(Citrus_greening)": "Huanglongbing (Citrus greening)",

    "Peach_Bacterial_spot": "Bacterial spot",
    "Peach_healthy": "Healthy",

    "Pepper_bell_Bacterial_spot": "Bacterial spot",
    "Pepper_bell_healthy": "Healthy",

    "Potato_Early_blight": "Early blight",
    "Potato_Late_blight": "Late blight",
    "Potato_healthy": "Healthy",

    "Raspberry_healthy": "Healthy",
    "Soybean_healthy": "Healthy",

    "Squash_Powdery_mildew": "Powdery mildew",

    "Strawberry_Leaf_scorch": "Leaf scorch",
    "Strawberry_healthy": "Healthy",

    "Tomato_Bacterial_spot": "Bacterial spot",
    "Tomato_Early_blight": "Early blight",
    "Tomato_Late_blight": "Late blight",
    "Tomato_Leaf_Mold": "Leaf mold",
    "Tomato_Septoria_leaf_spot": "Septoria leaf spot",
    "Tomato_Spider_mites_Two_spotted_spider_mite": "Spider mites",
    "Tomato_Target_Spot": "Target spot",
    "Tomato_Tomato_mosaic_virus": "Tomato mosaic virus",
    "Tomato_Tomato_Yellow_Leaf_Curl_Virus": "Yellow leaf curl virus",
    "Tomato_healthy": "Healthy"
}

def predict_disease(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img = image.img_to_array(img)

    # ResNet50 preprocessing
    img = preprocess_input(img)
    img = np.expand_dims(img, axis=0)

    preds = cnn_model.predict(img)
    class_id = int(np.argmax(preds))
    confidence = float(np.max(preds))

    raw_label = class_map[class_id]  # e.g. "Corn_Common_rust_"

    # ---- CLEAN & SPLIT ----
    raw_label = raw_label.strip("_")        # remove trailing _
    parts = raw_label.split("_", 1)

    crop = parts[0]
    disease = CLASS_MAP.get(raw_label,"Unknown disease")
    return crop, disease, confidence

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
    is_healthy = "healthy" in disease.lower()
    if not is_healthy and stress == "High":
        return "CRITICAL: Disease detected and plant under severe stress. Immediate treatment required."
    elif not is_healthy:
        return "WARNING: Disease detected. Monitor and apply treatment."
    elif stress == "High":
        return "PREVENTIVE: Plant under high stress. Check irrigation and nutrients."
    else:
        return "Healthy. No action required."
