"""Train an Explainable Boosting Machine (EBM) for 3-state diabetic risk classification.

States
------
0 = low      — glucose in range, vitals normal
1 = moderate — elevated glucose, compensated
2 = high     — hypo- or hyper-glycaemic emergency

Usage
-----
    python -m src.scripts.train_risk_ebm
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from interpret.glassbox import ExplainableBoostingClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

FEATURE_NAMES = [
    "age",
    "gender",           # encoded: 0 = M, 1 = F
    "bmi",
    "hba1c",
    "has_hypertension",
    "has_heart_disease",
    "medication_count",
    "glucose",
    "hr",
    "spo2",
    "steps",
    "sleep_hours",
    "confusion",
    "tremors",
    "thirst",
]
RISK_LABELS = ["low", "moderate", "high"]
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "risk_ebm.pkl"


# ── Synthetic data generation ─────────────────────────────────────────────────

def _generate_dataset(n_samples: int = 3000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows: list[dict] = []

    for _ in range(n_samples):
        age = int(rng.integers(20, 85))
        gender = int(rng.integers(0, 2))           # 0 = M, 1 = F
        bmi = float(rng.uniform(18.5, 40.0))
        hba1c = float(rng.uniform(5.0, 12.0))

        # Comorbidities more likely with age and high BMI
        has_hypertension = int(rng.random() < 0.15 + (age / 85) * 0.35 + (bmi - 18.5) / 200)
        has_heart_disease = int(rng.random() < 0.05 + (age / 85) * 0.20 + has_hypertension * 0.10)
        medication_count = int(rng.integers(0, 3 + has_hypertension + has_heart_disease + int(hba1c > 8.0)))

        sleep_hours = float(rng.uniform(4.0, 9.0))
        sleep_impact = (8.0 - sleep_hours) * 10.0 if sleep_hours < 7.0 else 0.0

        steps = int(rng.integers(500, 15000))
        step_impact = (steps / 1000.0) * -5.0

        # Assign target state with realistic class imbalance
        # High comorbidity load shifts toward moderate/high
        comorbidity_bias = 0.05 * (has_hypertension + has_heart_disease) + 0.03 * (hba1c > 8.0)
        p_low = max(0.1, 0.5 - comorbidity_bias)
        p_high = min(0.4, 0.2 + comorbidity_bias)
        p_mod = 1.0 - p_low - p_high
        target_state = int(rng.choice([0, 1, 2], p=[p_low, p_mod, p_high]))

        if target_state == 0:  # LOW risk
            glucose = float(rng.uniform(90.0, 140.0)) + sleep_impact + step_impact
            hr = int(rng.integers(60, 85))
            spo2 = int(rng.integers(96, 100))
        elif target_state == 1:  # MODERATE risk
            glucose = float(rng.uniform(160.0, 240.0)) + sleep_impact
            hr = int(rng.integers(80, 100))
            spo2 = int(rng.integers(94, 98))
        else:  # HIGH risk — hypoglycaemia or hyperglycaemic emergency
            is_hypo = rng.random() < 0.3
            if is_hypo:
                glucose = float(rng.uniform(40.0, 65.0))
                hr = int(rng.integers(105, 130))
            else:
                glucose = float(rng.uniform(260.0, 450.0))
                hr = int(rng.integers(90, 110))
            spo2 = int(rng.integers(90, 95))

        glucose = max(40.0, glucose)

        confusion = int(target_state == 2 and rng.random() < 0.7)
        tremors = int(glucose < 70.0 and rng.random() < 0.8)
        thirst = int(glucose > 200.0 and rng.random() < 0.6)

        rows.append({
            "age": age,
            "gender": gender,
            "bmi": bmi,
            "hba1c": hba1c,
            "has_hypertension": has_hypertension,
            "has_heart_disease": has_heart_disease,
            "medication_count": medication_count,
            "glucose": glucose,
            "hr": hr,
            "spo2": spo2,
            "steps": steps,
            "sleep_hours": sleep_hours,
            "confusion": confusion,
            "tremors": tremors,
            "thirst": thirst,
            "risk_state": target_state,
        })

    return pd.DataFrame(rows)


# ── Training ──────────────────────────────────────────────────────────────────

def train() -> None:
    print("Generating enhanced synthetic dataset …")
    df = _generate_dataset(2000)
    print(f"  {len(df)} samples — class distribution:\n{df['risk_state'].value_counts().to_string()}\n")

    X = df[FEATURE_NAMES].to_numpy()
    y = df["risk_state"].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Training Explainable Boosting Machine (multiclass) …")
    ebm = ExplainableBoostingClassifier(
        feature_names=FEATURE_NAMES,
        n_jobs=-1,
        random_state=42,
    )
    ebm.fit(X_train, y_train)

    print("\n--- Test-set performance ---")
    y_pred = ebm.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=RISK_LABELS))

    print("--- Global feature importances ---")
    importances = ebm.term_importances()
    for name, imp in sorted(zip(FEATURE_NAMES, importances), key=lambda x: -x[1]):
        print(f"  {name:<15} {imp:.4f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(ebm, MODEL_PATH)
    print(f"\nModel saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()
