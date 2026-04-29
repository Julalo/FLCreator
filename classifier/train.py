"""
train.py — Train the Random Forest drum classifier.

Usage:
    python -m classifier.train --data_dir training_data/

Expected layout of training_data/:
    training_data/
    ├── kick/      *.wav *.mp3 ...
    ├── snare/
    ├── hihat_closed/
    ...

The trained model is saved to classifier/drum_classifier.joblib.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif"}
MODEL_PATH = Path(__file__).parent / "drum_classifier.joblib"

VALID_LABELS = [
    "kick", "snare", "hihat_closed", "hihat_open", "clap",
    "tom", "crash", "ride", "percussion", "808",
    "fx", "loop", "one_shot", "vocal", "other",
]


def collect_dataset(data_dir: Path) -> tuple[list, list]:
    from .features import extract_features

    X, y = [], []
    for label_dir in sorted(data_dir.iterdir()):
        if not label_dir.is_dir():
            continue
        label = label_dir.name.lower()
        if label not in VALID_LABELS:
            print(f"[warn] Unknown label directory '{label}' — skipping")
            continue
        files = [f for f in label_dir.rglob("*") if f.suffix.lower() in AUDIO_EXTS]
        print(f"  {label}: {len(files)} files")
        for f in files:
            features = extract_features(str(f))
            X.append(features)
            y.append(label)
    return X, y


def train(data_dir: Path, n_estimators: int = 200, test_split: float = 0.2) -> None:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier  # type: ignore
    from sklearn.model_selection import train_test_split  # type: ignore
    from sklearn.metrics import classification_report  # type: ignore
    import joblib  # type: ignore

    print(f"Collecting samples from {data_dir} ...")
    X_raw, y_raw = collect_dataset(data_dir)

    if len(X_raw) == 0:
        print("No samples found — aborting.")
        sys.exit(1)

    X = np.array(X_raw, dtype=np.float32)
    y = np.array(y_raw)

    print(f"Total samples: {len(X)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_split, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=None,
        min_samples_split=2,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    print("Training Random Forest ...")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print("\nClassification report:")
    print(classification_report(y_test, y_pred))

    joblib.dump(clf, MODEL_PATH)
    print(f"\nModel saved to {MODEL_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train FL Studio drum classifier")
    parser.add_argument("--data_dir", type=Path, default=Path("training_data"),
                        help="Directory with labelled sub-folders")
    parser.add_argument("--n_estimators", type=int, default=200)
    parser.add_argument("--test_split", type=float, default=0.2)
    args = parser.parse_args()

    if not args.data_dir.is_dir():
        print(f"Error: {args.data_dir} is not a directory.")
        sys.exit(1)

    train(args.data_dir, args.n_estimators, args.test_split)


if __name__ == "__main__":
    main()
