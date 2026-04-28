"""Train a Decision Tree classifier for chronic disease risk stratification.

Generates synthetic clinical data reflecting Type-2 Diabetes management rules
and serialises the trained model to models/risk_tree.pkl.

Usage:
    python scripts/train_risk_tree.py
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text

RNG = np.random.default_rng(42)
N = 2_000

FEATURE_NAMES = [
    "age",
    "bmi",
    "hba1c_last",
    "baseline_glucose",
    "current_glucose",
    "symptom_count",
    "has_hypertension",
    "has_heart_disease",
    "medication_count",
]
RISK_LABELS = ["low", "medium", "high"]
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "risk_tree.pkl"


def _generate_dataset() -> pd.DataFrame:
    age = RNG.integers(25, 80, size=N).astype(float)
    bmi = RNG.uniform(18.5, 45.0, size=N)
    hba1c = RNG.uniform(5.5, 12.0, size=N)
    baseline_glucose = RNG.uniform(4.0, 15.0, size=N)
    current_glucose = baseline_glucose + RNG.uniform(-1.5, 3.0, size=N)
    current_glucose = np.clip(current_glucose, 3.0, 18.0)
    symptom_count = RNG.integers(0, 7, size=N).astype(float)
    has_hypertension = RNG.integers(0, 2, size=N).astype(float)
    has_heart_disease = RNG.integers(0, 2, size=N).astype(float)
    medication_count = RNG.integers(0, 6, size=N).astype(float)

    # Clinical rule-based labelling
    score = np.zeros(N)
    score += np.where(hba1c >= 9.0, 2, np.where(hba1c >= 7.0, 1, 0))
    score += np.where(current_glucose >= 11.1, 2, np.where(current_glucose >= 7.8, 1, 0))
    score += np.where(bmi >= 35.0, 1, 0)
    score += np.where(age >= 65, 1, 0)
    score += np.where(has_hypertension == 1, 1, 0)
    score += np.where(has_heart_disease == 1, 1, 0)
    score += np.where(symptom_count >= 3, 1, 0)

    label = np.where(score >= 5, 2, np.where(score >= 2, 1, 0))

    # Add 5 % label noise for realism
    noise_mask = RNG.random(N) < 0.05
    label[noise_mask] = RNG.integers(0, 3, size=noise_mask.sum())

    return pd.DataFrame(
        {
            "age": age,
            "bmi": bmi,
            "hba1c_last": hba1c,
            "baseline_glucose": baseline_glucose,
            "current_glucose": current_glucose,
            "symptom_count": symptom_count,
            "has_hypertension": has_hypertension,
            "has_heart_disease": has_heart_disease,
            "medication_count": medication_count,
            "risk_level": label,
        }
    )


def train() -> None:
    print("Generating synthetic clinical dataset …")
    df = _generate_dataset()

    X = df[FEATURE_NAMES].to_numpy()
    y = df["risk_level"].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Training Decision Tree …")
    clf = DecisionTreeClassifier(
        max_depth=6,
        min_samples_leaf=10,
        class_weight="balanced",
        random_state=42,
    )
    clf.fit(X_train, y_train)

    print("\n--- Test-set performance ---")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=RISK_LABELS))

    print("--- Decision Tree (first 5 levels) ---")
    print(export_text(clf, feature_names=FEATURE_NAMES, max_depth=5))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"Model saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()
