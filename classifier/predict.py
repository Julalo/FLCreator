"""
predict.py — Three-tier sample type classifier.

Tier 1: scikit-learn Random Forest (if drum_classifier.joblib exists)
Tier 2: Filename keyword heuristics
Tier 3: Spectral heuristics from librosa features
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .features import extract_features

MODEL_PATH = Path(__file__).parent / "drum_classifier.joblib"

_MODEL = None
_MODEL_LOADED = False

LABELS = [
    "kick", "snare", "hihat_closed", "hihat_open", "clap",
    "tom", "crash", "ride", "percussion", "808",
    "fx", "loop", "one_shot", "vocal", "other",
]

_FILENAME_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(kick|kik|bd|bass.?drum)\b", re.I), "kick"),
    (re.compile(r"\b(snare|snr|sn|rimshot|rim)\b", re.I), "snare"),
    (re.compile(r"\b(clap|clp|handclap)\b", re.I), "clap"),
    (re.compile(r"\b(hat|hh|hihat|hi.?hat|closed.?hat|chh)\b", re.I), "hihat_closed"),
    (re.compile(r"\b(open.?hat|ohh)\b", re.I), "hihat_open"),
    (re.compile(r"\b(808|sub)\b", re.I), "808"),
    (re.compile(r"\b(tom|floor.?tom|rack.?tom)\b", re.I), "tom"),
    (re.compile(r"\b(crash|cymbal)\b", re.I), "crash"),
    (re.compile(r"\b(ride)\b", re.I), "ride"),
    (re.compile(r"\b(perc|shaker|tamb|cabasa|conga|bongo|cowbell)\b", re.I), "percussion"),
    (re.compile(r"\b(fx|sfx|effect|riser|sweep|impact|hit)\b", re.I), "fx"),
    (re.compile(r"\b(loop|phrase|groove|beat)\b", re.I), "loop"),
    (re.compile(r"\b(vox|vocal|voice|choir|adlib|acapella)\b", re.I), "vocal"),
    (re.compile(r"\b(one.?shot|oneshot)\b", re.I), "one_shot"),
]


def _load_model():
    global _MODEL, _MODEL_LOADED
    if _MODEL_LOADED:
        return _MODEL
    _MODEL_LOADED = True
    if MODEL_PATH.exists():
        try:
            import joblib  # type: ignore
            _MODEL = joblib.load(MODEL_PATH)
        except Exception:
            _MODEL = None
    return _MODEL


def _classify_by_filename(file_path: str) -> str | None:
    stem = Path(file_path).stem
    for pattern, label in _FILENAME_PATTERNS:
        if pattern.search(stem):
            return label
    return None


def _classify_by_spectrum(features: np.ndarray) -> str:
    """
    Heuristic classification from the raw feature vector.
    Uses: centroid [26], rolloff [28], zcr [29], rms_mean [30],
          hf_ratio [35], duration [33], tempo [32].
    """
    centroid = float(features[26])
    rolloff = float(features[28])
    zcr = float(features[29])
    rms_mean = float(features[30])
    hf_ratio = float(features[35])
    duration = float(features[33])
    tempo = float(features[32])

    # Loops: long duration with detectable tempo
    if duration > 1.5 and tempo > 60:
        return "loop"

    # 808 / sub: very low centroid, long duration, low ZCR
    if centroid < 500 and duration > 0.3 and zcr < 0.05:
        return "808"

    # Kick: low centroid, moderate duration, low ZCR
    if centroid < 2000 and zcr < 0.15 and duration < 1.0:
        return "kick"

    # Hihat (closed): very high centroid + hf_ratio, short
    if centroid > 7000 and hf_ratio > 0.5 and duration < 0.3:
        return "hihat_closed"

    # Hihat (open): high centroid, slightly longer
    if centroid > 6000 and hf_ratio > 0.4 and 0.3 <= duration < 1.0:
        return "hihat_open"

    # Snare: mid centroid, high ZCR (noisy transient)
    if 1500 < centroid < 6000 and zcr > 0.2 and duration < 0.8:
        return "snare"

    # Clap: similar to snare but very short
    if centroid > 3000 and zcr > 0.25 and duration < 0.3:
        return "clap"

    # Crash: high centroid, long decay
    if centroid > 5000 and duration > 0.8:
        return "crash"

    # FX: medium-long, varied
    if duration > 1.0:
        return "fx"

    return "other"


def predict_sample_type(file_path: str) -> tuple[str, float]:
    """
    Returns (label, confidence).

    Confidence scale:
      0.9+ → ML model high confidence
      0.85  → filename heuristic match
      0.6   → ML model medium confidence
      0.5   → spectral heuristic
    """
    features = extract_features(file_path)

    # Tier 1: ML model
    model = _load_model()
    if model is not None:
        try:
            proba = model.predict_proba([features])[0]
            best_idx = int(np.argmax(proba))
            confidence = float(proba[best_idx])
            label = LABELS[best_idx]
            if confidence >= 0.6:
                return label, confidence
            # Model is uncertain — fall through but remember its vote
            ml_label, ml_conf = label, confidence
        except Exception:
            ml_label, ml_conf = None, 0.0
    else:
        ml_label, ml_conf = None, 0.0

    # Tier 2: Filename heuristics
    name_label = _classify_by_filename(file_path)
    if name_label:
        return name_label, 0.85

    # Return ML vote even if low confidence, before spectral fallback
    if ml_label and ml_conf >= 0.35:
        return ml_label, ml_conf

    # Tier 3: Spectral heuristics
    return _classify_by_spectrum(features), 0.5
