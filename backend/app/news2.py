"""NEWS2 parameter scoring reference implementation.

Bands follow the Royal College of Physicians NEWS2 chart (2017). This software
must not be treated as a clinically validated device; incomplete observations
produce an explicit incomplete result rather than fabricated scores.
"""
from __future__ import annotations

from typing import Any


def score_news2(values: dict[str, Any]) -> dict[str, Any]:
    required = ("respiratory_rate", "spo2", "systolic_bp", "heart_rate", "temperature", "consciousness")
    missing = [name for name in required if values.get(name) in (None, "")]
    oxygen = bool(values.get("supplemental_oxygen", False))
    scale = int(values.get("spo2_scale", 1))
    if scale == 2 and not bool(values.get("scale2_authorized", False)):
        raise ValueError("SpO2 Scale 2 requires explicit authorization")
    rr = float(values["respiratory_rate"]) if values.get("respiratory_rate") is not None else None
    spo2 = float(values["spo2"]) if values.get("spo2") is not None else None
    systolic = float(values["systolic_bp"]) if values.get("systolic_bp") is not None else None
    pulse = float(values["heart_rate"]) if values.get("heart_rate") is not None else None
    temperature = float(values["temperature"]) if values.get("temperature") is not None else None
    consciousness = str(values["consciousness"]) if values.get("consciousness") is not None else None

    respiratory_score = None if rr is None else (3 if rr <= 8 or rr >= 25 else 1 if 9 <= rr <= 11 else 2 if 21 <= rr <= 24 else 0)
    if scale == 1:
        spo2_score = None if spo2 is None else (3 if spo2 <= 91 else 2 if spo2 <= 93 else 1 if spo2 <= 95 else 0)
    else:
        spo2_score = None if spo2 is None else (3 if spo2 >= 97 else 2 if spo2 >= 95 else 1 if spo2 >= 93 else 0 if spo2 >= 88 else 1 if spo2 >= 86 else 2 if spo2 >= 84 else 3) if oxygen else (0 if spo2 >= 88 else 1 if spo2 >= 86 else 2 if spo2 >= 84 else 3)
    systolic_score = None if systolic is None else (3 if systolic <= 90 or systolic >= 220 else 2 if systolic <= 100 else 1 if systolic <= 110 else 0)
    pulse_score = None if pulse is None else (3 if pulse <= 40 or pulse >= 131 else 1 if pulse <= 50 or (91 <= pulse <= 110) else 2 if 111 <= pulse <= 130 else 0)
    consciousness_score = None if consciousness is None else (0 if consciousness == "alert" else 3)
    temperature_score = None if temperature is None else (3 if temperature <= 35.0 else 1 if temperature <= 36.0 else 0 if temperature <= 38.0 else 1 if temperature <= 39.0 else 2)
    oxygen_score = 2 if oxygen else 0
    components = {"respiratory_rate": respiratory_score, "spo2": spo2_score, "supplemental_oxygen": oxygen_score, "systolic_bp": systolic_score, "heart_rate": pulse_score, "consciousness": consciousness_score, "temperature": temperature_score}
    return {
        "score_name": "NEWS2",
        "score_version": "RCP NEWS2 chart (2017)",
        "parameter_scores": components,
        "total_score": sum(score for score in components.values() if score is not None),
        "missing_parameters": [name for name, score in components.items() if score is None],
        "complete": not any(score is None for score in components.values()),
        "spo2_scale": scale,
        "supplemental_oxygen": oxygen,
        "demo_only": False,
        "clinically_validated_implementation": False,
        "implementation_status": "reference_implementation_unvalidated",
        "disclaimer": "Reference implementation only. Verify against the official RCP chart and local policy before any clinical use; not a diagnosis or treatment recommendation.",
    }
