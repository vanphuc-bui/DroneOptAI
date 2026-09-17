from __future__ import annotations
import json, os
import numpy as np
import joblib

FEATURES = ["distance_km","payload_kg","altitude_m","planned_speed_ms","wind_speed_ms","temperature_c","humidity_pct","battery_soh"]
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(os.path.dirname(__file__), "energy_model.joblib"))

def feature_vector(mission, battery_soh: float):
    return {
        "distance_km": mission.distance_km,
        "payload_kg": mission.payload_kg,
        "altitude_m": mission.altitude_m,
        "planned_speed_ms": mission.planned_speed_ms,
        "wind_speed_ms": mission.wind_speed_ms,
        "temperature_c": mission.temperature_c,
        "humidity_pct": mission.humidity_pct,
        "battery_soh": battery_soh,
    }

def _fallback_energy(x: dict) -> float:
    base = 22 + 13.5*x["distance_km"] + 10.5*x["payload_kg"] + 0.035*x["altitude_m"]
    aero = 1.4*max(x["planned_speed_ms"]-8, 0) + 2.8*max(x["wind_speed_ms"], 0)
    climate = 0.08*abs(x["temperature_c"]-20) + 0.015*abs(x["humidity_pct"]-50)
    health = max(0, (100-x["battery_soh"])*0.55)
    return float(max(8, base+aero+climate+health))

def predict(mission, battery_soh: float = 100.0):
    x = feature_vector(mission, battery_soh)
    energy = _fallback_energy(x)
    model_version = "physics-informed-demo-v1"
    model = None
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            energy = float(model.predict(np.array([[x[f] for f in FEATURES]], dtype=float))[0])
            model_version = "gradient-boosting-v1"
        except Exception:
            pass
    duration_min = mission.distance_km*1000/max(mission.planned_speed_ms, 0.1)/60
    efficiency = mission.distance_km*1000/max(energy, 1e-6)
    capacity_proxy = 240 * battery_soh/100
    margin = capacity_proxy-energy
    risk = "high" if margin < 25 or mission.wind_speed_ms > 12 else "medium" if margin < 60 or mission.wind_speed_ms > 8 else "low"
    contributions = {
        "distance": round(13.5*x["distance_km"],2),
        "payload": round(10.5*x["payload_kg"],2),
        "altitude": round(0.035*x["altitude_m"],2),
        "wind": round(2.8*max(x["wind_speed_ms"],0),2),
        "battery_health_penalty": round(max(0,(100-battery_soh)*0.55),2),
    }
    try:
        if model is not None:
            import shap
            exp = shap.Explainer(model, np.array([[x[f] for f in FEATURES]], dtype=float))
            values = exp(np.array([[x[f] for f in FEATURES]], dtype=float)).values[0]
            contributions = {f: round(float(v), 3) for f,v in zip(FEATURES, values)}
    except Exception:
        pass
    top = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:3]
    recommendation = "Mission feasible."
    if risk == "high": recommendation = "Re-plan mission: reduce payload, choose a calmer weather window, or use a healthier battery."
    elif risk == "medium": recommendation = "Proceed conditionally and verify battery reserve before approval."
    recommendation += " Main energy drivers: " + ", ".join(k for k,_ in top) + "."
    return {
        "model_version": model_version,
        "energy_wh": round(energy,2),
        "duration_min": round(duration_min,2),
        "efficiency_m_per_wh": round(efficiency,2),
        "risk_level": risk,
        "explanation": {"method": "SHAP when trained model is available; transparent contribution fallback otherwise", "feature_contributions": contributions, "top_factors": top},
        "recommendation": recommendation,
    }
