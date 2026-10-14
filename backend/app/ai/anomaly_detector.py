"""
AI Anomaly Detection Engine for SATYA AI.

Trains an Isolation Forest over engineered behavioural features from
audit logs, then converts the raw anomaly score into a 0-100 risk score.
Designed to be re-trained periodically (e.g. nightly) on the growing
audit_logs collection.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURE_COLUMNS = [
    "hour_of_day",
    "is_new_device",
    "is_new_ip",
    "is_failed_login",
    "downloads_last_hour",
    "locations_last_24h",
    "is_bulk_download",
    "skipped_approval",
    "permission_escalation",
]


@dataclass
class AnomalyResult:
    risk_score: float          # 0-100
    is_anomaly: bool
    raw_score: float           # sklearn's decision_function output


class AnomalyDetector:
    def __init__(self, contamination: float = 0.08, random_state: int = 42):
        self.model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=random_state,
        )
        self._is_fitted = False

    def fit(self, logs_df: pd.DataFrame) -> None:
        X = logs_df[FEATURE_COLUMNS].fillna(0)
        self.model.fit(X)
        self._is_fitted = True

    def score(self, feature_row: dict) -> AnomalyResult:
        if not self._is_fitted:
            raise RuntimeError("AnomalyDetector must be fit() before scoring.")
        X = pd.DataFrame([feature_row])[FEATURE_COLUMNS].fillna(0)
        raw_score = self.model.decision_function(X)[0]      # higher = more normal
        prediction = self.model.predict(X)[0]                 # -1 anomaly, 1 normal

        # Convert raw_score (~ -0.5 to 0.5) into an intuitive 0-100 risk score,
        # where higher risk = more anomalous.
        risk_score = float(np.clip((0.5 - raw_score) * 100, 0, 100))
        return AnomalyResult(
            risk_score=round(risk_score, 1),
            is_anomaly=prediction == -1,
            raw_score=float(raw_score),
        )


def risk_level_from_score(score: float) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"
