"""
Explainable AI layer.

The Isolation Forest gives us *that* something looks anomalous but not
*why* in human terms. This module turns the same feature row into a
plain-language list of contributing factors, a confidence estimate, and
a recommended action -- so every alert an investigator sees is
justified, not a black box.
"""
from dataclasses import dataclass


@dataclass
class Explanation:
    reasons: list[str]
    confidence: float
    recommended_action: str


# Each rule: (feature_check, human_readable_reason, weight)
def _build_rules(features: dict) -> list[tuple[bool, str, float]]:
    hour = features.get("hour_of_day", 12)
    return [
        (hour < 6 or hour >= 23, f"Login/activity occurred at an unusual hour ({hour:02d}:00)", 0.20),
        (bool(features.get("is_new_device")), "Action performed from a previously unseen device", 0.18),
        (bool(features.get("is_new_ip")), "Action originated from an unrecognized IP address", 0.15),
        (bool(features.get("is_failed_login")), "Preceded by one or more failed login attempts", 0.12),
        (features.get("downloads_last_hour", 0) >= 3, "Paper downloaded multiple times within a short window", 0.15),
        (features.get("locations_last_24h", 1) > 1, "Same account accessed from multiple locations within 24 hours", 0.12),
        (bool(features.get("is_bulk_download")), "Unusually large number of papers downloaded in one session", 0.15),
        (bool(features.get("skipped_approval")), "Paper was distributed without completing the approval workflow", 0.20),
        (bool(features.get("permission_escalation")), "User's permission level was escalated shortly before this action", 0.18),
    ]


def explain(features: dict, risk_score: float) -> Explanation:
    rules = _build_rules(features)
    triggered = [(reason, weight) for (cond, reason, weight) in rules if cond]

    reasons = [r for r, _ in triggered] or ["No single dominant factor -- flagged by overall behavioural deviation"]
    confidence = min(0.99, 0.5 + sum(w for _, w in triggered))

    if risk_score >= 80:
        action = "Suspend account immediately and escalate to Security Auditor for investigation."
    elif risk_score >= 60:
        action = "Flag account for manual review; restrict further downloads pending confirmation."
    elif risk_score >= 35:
        action = "Monitor account closely over the next 24 hours; no immediate action required."
    else:
        action = "No action needed -- behaviour within normal range."

    return Explanation(reasons=reasons, confidence=round(confidence, 2), recommended_action=action)
