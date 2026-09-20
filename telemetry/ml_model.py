"""
Machine Learning inference service for AI Predictive Maintenance in Django.
Loads the trained Random Forest model and performs real-time failure risk classification.
"""
import os
import joblib
import pandas as pd
from typing import Dict, Any
from django.conf import settings

_model = None

STATUS_LABELS = ["NORMAL", "WARNING", "HIGH FAILURE RISK"]


def get_model():
    """Load and cache the scikit-learn failure prediction model."""
    global _model
    if _model is not None:
        return _model

    candidate_paths = [
        getattr(settings, 'MODEL_PATH', None),
        settings.BASE_DIR / 'model' / 'failure_model.pkl',
        settings.BASE_DIR / 'backend' / 'model' / 'failure_model.pkl',
    ]

    for path in candidate_paths:
        if path and os.path.exists(str(path)):
            try:
                _model = joblib.load(str(path))
                return _model
            except Exception as e:
                print(f"[Warning] Failed to load model from {path}: {e}")

    raise FileNotFoundError(
        f"Predictive maintenance model failure_model.pkl not found in expected paths. "
        f"Please verify model file exists."
    )


def predict_risk(temperature: float, vibration: float, current: float, rpm: int) -> Dict[str, Any]:
    """
    Given 4 sensor telemetry features:
      - temperature (°C)
      - vibration (mm/s)
      - current (A)
      - rpm (RPM)
    
    Returns:
      {
        "predicted_class": 0, 1, or 2,
        "status": "NORMAL" | "WARNING" | "HIGH FAILURE RISK",
        "risk_percent": float (0-100),
        "probabilities": [prob_normal, prob_warning, prob_high_risk]
      }
    """
    model = get_model()
    features = pd.DataFrame(
        [[temperature, vibration, current, rpm]],
        columns=["temperature", "vibration", "current", "rpm"]
    )
    predicted_class = int(model.predict(features)[0])
    probabilities = model.predict_proba(features)[0]
    
    prob_high_risk = float(probabilities[2]) if len(probabilities) > 2 else 0.0
    prob_warning = float(probabilities[1]) if len(probabilities) > 1 else 0.0

    # Smooth continuous composite risk calculation:
    # High risk probability scales to 100%, warning probability scales to ~45%
    # with progressive physical penalty for gradual thermal & mechanical wear
    composite_risk = prob_high_risk * 100.0 + prob_warning * 45.0
    temp_penalty = max(0.0, (temperature - 68.0) * 0.75)
    vib_penalty = max(0.0, (vibration - 2.0) * 4.0)

    final_risk = min(100.0, composite_risk + temp_penalty + vib_penalty)
    status = STATUS_LABELS[predicted_class] if 0 <= predicted_class < len(STATUS_LABELS) else "UNKNOWN"

    return {
        "predicted_class": predicted_class,
        "status": status,
        "risk_percent": round(final_risk, 1),
        "probabilities": [round(float(p), 4) for p in probabilities],
    }
