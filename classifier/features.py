"""
features.py — Extracts a fixed-length feature vector from an audio file using librosa.

Feature vector layout (37 values total):
  [0:13]   MFCC means (13)
  [13:26]  MFCC std devs (13)
  [26]     Spectral centroid mean
  [27]     Spectral bandwidth mean
  [28]     Spectral rolloff mean
  [29]     Zero crossing rate mean
  [30]     RMS mean
  [31]     RMS max
  [32]     Estimated tempo
  [33]     Duration in seconds
  [34]     Low-energy ratio  (fraction of frames below 10% of max RMS — helps ID hihats)
  [35]     High-frequency ratio  (fraction of spectral energy above 4kHz)
  [36]     Onset strength mean
"""

from __future__ import annotations

import numpy as np

FEATURE_SIZE = 37


def extract_features(file_path: str, sr: int = 22050) -> np.ndarray:
    """Return a 1-D numpy array of length FEATURE_SIZE, or zeros on error."""
    try:
        import librosa  # type: ignore
    except ImportError:
        return np.zeros(FEATURE_SIZE, dtype=np.float32)

    try:
        y, sr = librosa.load(file_path, sr=sr, mono=True, duration=10.0)
    except Exception:
        return np.zeros(FEATURE_SIZE, dtype=np.float32)

    if len(y) == 0:
        return np.zeros(FEATURE_SIZE, dtype=np.float32)

    # MFCCs
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = mfcc.mean(axis=1)
    mfcc_std = mfcc.std(axis=1)

    # Spectral features
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr).mean()
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr).mean()
    zcr = librosa.feature.zero_crossing_rate(y).mean()

    # Energy
    rms = librosa.feature.rms(y=y)[0]
    rms_mean = rms.mean()
    rms_max = rms.max()

    # Rhythm
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(tempo) if np.isscalar(tempo) else float(tempo[0]) if len(tempo) > 0 else 0.0

    # Duration
    duration = librosa.get_duration(y=y, sr=sr)

    # Low-energy ratio
    low_energy_ratio = float((rms < 0.1 * rms_max).mean()) if rms_max > 0 else 0.0

    # High-frequency energy ratio (energy above 4kHz vs total)
    stft = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    high_mask = freqs >= 4000
    hf_energy = stft[high_mask, :].sum()
    total_energy = stft.sum() + 1e-8
    hf_ratio = float(hf_energy / total_energy)

    # Onset strength
    onset_strength = librosa.onset.onset_strength(y=y, sr=sr).mean()

    vec = np.concatenate([
        mfcc_mean,
        mfcc_std,
        [centroid, bandwidth, rolloff, zcr,
         rms_mean, rms_max, tempo_val, duration,
         low_energy_ratio, hf_ratio, onset_strength],
    ]).astype(np.float32)

    return vec
