import os
import json
import numpy as np
from django.conf import settings

# ===== TensorFlow (Backup Model) =====
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input

# ===== PyTorch (Main Model) =====
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image

# ===== PATHS =====
MODEL_DIR = os.path.join(settings.BASE_DIR, "model")

KERAS_MODEL_PATH = os.path.join(MODEL_DIR, "agrotech_resnet50.h5")
PTH_MODEL_PATH = os.path.join(MODEL_DIR, "crop_model_v2.pth")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.set_num_threads(1)

# ===== LOAD CLASS MAP =====
with open(os.path.join(MODEL_DIR, "class_indices.json")) as f:
    class_map = json.load(f)
    class_map = {v: k for k, v in class_map.items()}

PTH_CLASS_NAMES = list(class_map.values())

# ===== LOAD CROP PROFILES =====
with open(os.path.join(MODEL_DIR, "crop_data.json")) as f:
    CROP_PROFILES = json.load(f)

# ===== HUMAN READABLE LABELS =====
CLASS_MAP = {
    "Apple_Apple_scab": "Apple scab",
    "Apple_Black_rot": "Black rot",
    "Apple_Cedar_apple_rust": "Cedar apple rust",
    "Apple_healthy": "Healthy",

    "Blueberry_healthy": "Healthy",

    "Cherry_(including_sour)_healthy": "Healthy",
    "Cherry_(including_sour)_Powdery_mildew": "Powdery mildew",

    "Corn_(maize)_Cercospora_leaf_spot_Gray_leaf_spot": "Gray leaf spot",
    "Corn_(maize)_Common_rust": "Common rust",
    "Corn_(maize)_Northern_Leaf_Blight": "Northern leaf blight",
    "Corn_(maize)_healthy": "Healthy",

    "Grape_Black_rot": "Black rot",
    "Grape_Esca_(Black_Measles)": "Esca (Black measles)",
    "Grape_Leaf_blight_(Isariopsis_Leaf_Spot)": "Leaf blight",
    "Grape_healthy": "Healthy",

    "Orange_Huanglongbing_(Citrus_greening)": "Citrus greening",

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

# =========================================================
# 🔹 MODEL LOADERS
# =========================================================

keras_model = None
pth_model = None


def get_keras_model():
    global keras_model
    if keras_model is None:
        keras_model = load_model(KERAS_MODEL_PATH)
    return keras_model


def get_pth_model():
    global pth_model

    if pth_model is None:
        # ✅ Use MobileNetV2 instead of ResNet
        model = models.mobilenet_v2(weights=None)

        # Replace classifier
        model.classifier[1] = nn.Linear(
            model.last_channel,
            len(PTH_CLASS_NAMES)
        )

        model.load_state_dict(torch.load(PTH_MODEL_PATH, map_location=DEVICE))
        model.to(DEVICE)
        model.eval()

        pth_model = model

    return pth_model


# =========================================================
# 🔹 PREPROCESSING
# =========================================================

pth_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# =========================================================
# 🔹 PREDICTION FUNCTIONS
# =========================================================

def predict_disease_pth(img_path):
    model = get_pth_model()

    image = Image.open(img_path).convert("RGB")
    image = pth_transform(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = model(image)
        probs = torch.softmax(outputs, dim=1)[0]

    confidence, class_id = torch.max(probs, 0)

    raw_label = PTH_CLASS_NAMES[class_id.item()].strip("_")
    crop = raw_label.split("_", 1)[0]
    disease = CLASS_MAP.get(raw_label, "Unknown disease")

    return crop, disease, round(float(confidence.item()) * 100, 2)


def predict_disease_keras(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img = image.img_to_array(img)

    img = preprocess_input(img)
    img = np.expand_dims(img, axis=0)

    model = get_keras_model()
    preds = model.predict(img)

    class_id = int(np.argmax(preds))
    confidence = float(np.max(preds))

    raw_label = class_map[class_id].strip("_")
    crop = raw_label.split("_", 1)[0]
    disease = CLASS_MAP.get(raw_label, "Unknown disease")

    return crop, disease, round(confidence * 100, 2)


# =========================================================
# 🔥 MAIN PREDICTION FUNCTION
# =========================================================

def predict_disease(img_path):
    # Primary model (PyTorch)
    crop, disease, confidence = predict_disease_pth(img_path)

    # Fallback logic
    if confidence < 70:
        try:
            return predict_disease_keras(img_path)
        except:
            pass

    return crop, disease, confidence


# =========================================================
# 🔹 STRESS ANALYSIS
# =========================================================

def normalize_crop(crop):
    return str(crop).strip().lower()


def predict_stress(crop, temp, humidity, moisture, ph):
    crop = normalize_crop(crop)

    if crop not in CROP_PROFILES:
        return "UNKNOWN"

    profile = CROP_PROFILES[crop]
    risk = 0

    if not (profile["temperature"]["min"] <= temp <= profile["temperature"]["max"]):
        risk += 2

    if not (profile["humidity"]["min"] <= humidity <= profile["humidity"]["max"]):
        risk += 1

    if not (profile["soil_moisture"]["min"] <= moisture <= profile["soil_moisture"]["max"]):
        risk += 2

    if not (profile["soil_pH"]["min"] <= ph <= profile["soil_pH"]["max"]):
        risk += 1

    if risk <= 1:
        return "LOW"
    elif risk <= 3:
        return "MEDIUM"
    else:
        return "HIGH"


# =========================================================
# 🔹 FINAL DECISION ENGINE
# =========================================================

def agrotech_decision(disease, stress):
    is_healthy = "healthy" in disease.lower()

    if not is_healthy and stress == "HIGH":
        return "CRITICAL: Disease detected with unfavorable environmental conditions. Immediate treatment required."
    elif not is_healthy:
        return "WARNING: Disease detected. Monitor crop and apply recommended treatment."
    elif stress == "HIGH":
        return "PREVENTIVE ALERT: Crop under environmental stress. Adjust irrigation or nutrients."
    elif stress == "MEDIUM":
        return "CAUTION: Slight stress detected. Monitor crop conditions."
    else:
        return "NORMAL: Crop is healthy and conditions are optimal."