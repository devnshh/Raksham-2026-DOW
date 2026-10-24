"""
satark_scorer.py: serving wrapper for the trained bundle (satark_model.joblib, built by ml/train.py).
"""
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

warnings.filterwarnings("ignore")

# Representative note per intent (stopgap, see module docstring). 'none' -> empty note.
INTENT_TEXT = {
    "none": "", "food": "dinner", "home": "rent", "family": "family", "misc": "misc",
    "task": "task deposit", "kyc": "kyc update", "legal": "RBI verification fee",
    "investment": "investment profit", "refund": "refund", "receive": "receive payment",
}

# feature -> reason code (only features that pushed the score UP are reported)
REASON_MAP = {
    "on_call": "ON_CALL", "screen_shared": "SCREEN_SHARED", "remote_app_new": "REMOTE_APP_NEW",
    "remote_app_present": "REMOTE_APP_PRESENT", "device_new": "NEW_DEVICE",
    "payee_first_time": "NEW_PAYEE", "payee_age_days": "NEW_PAYEE_YOUNG_ACCOUNT",
    "payee_verified": "UNVERIFIED_PAYEE", "payee_new_payers_24h": "FAN_IN_24H",
    "payee_reports_prior": "PAYEE_REPORTED", "lookalike_score": "LOOKALIKE_HANDLE",
    "amount": "AMOUNT_UNUSUAL", "amount_ratio": "AMOUNT_UNUSUAL", "amount_z": "AMOUNT_UNUSUAL",
    "amount_vs_max": "AMOUNT_UNUSUAL", "hour": "UNUSUAL_HOUR", "hour_familiarity": "UNUSUAL_HOUR",
    "link_bad": "BAD_LINK", "link_domain_age_days": "BAD_LINK", "secs_link_to_pay": "LINK_ENTRY",
    "escalation_ratio": "ESCALATING_PAYMENTS", "same_payee_count_24h": "REPEAT_PAYEE_24H",
    "same_payee_sum_24h": "REPEAT_PAYEE_24H", "note_risk": "NOTE_INTENT_RISK",
    "app_switches": "SESSION_PRESSURE", "typing_z": "SESSION_PRESSURE", "pause_z": "SESSION_PRESSURE",
    "pin_time_z": "SESSION_PRESSURE", "failed_auth": "FAILED_AUTH",
    "entry_qr_scan": "QR_ENTRY", "entry_qr_gallery": "QR_ENTRY",
    "entry_deep_link_sms": "LINK_ENTRY", "entry_deep_link_whatsapp": "LINK_ENTRY",
}
LINK_COLS = ["link_bad", "link_domain_age_days", "secs_link_to_pay"]
_BOOL_RISK = {"on_call", "screen_shared", "remote_app_new", "remote_app_present", "device_new", "payee_first_time"}


def _is_risky(col, row):
    """True only if this feature is actually in its risky state for this payment.
    SHAP can push the score up for a benign value (e.g. entry_qr_scan=0); such
    features must never be shown to the user as a reason."""
    v = row[col]
    g = row.get  # other columns may be absent from a bundle; default to non-risky values
    if col in _BOOL_RISK:
        return bool(v)
    if col == "payee_age_days":
        return 0 <= v <= 30
    if col == "payee_verified":
        return not bool(v)
    if col == "payee_new_payers_24h":
        return v >= 5
    if col == "payee_reports_prior":
        return v >= 1
    if col == "lookalike_score":
        return v >= 0.7
    if col in ("amount", "amount_ratio", "amount_z", "amount_vs_max"):
        return g("amount_ratio", 0) >= 2 or g("amount_z", 0) >= 2
    if col in ("hour", "hour_familiarity"):
        return g("hour_familiarity", 1) <= 0.1
    if col == "link_bad":
        return v == 1
    if col == "link_domain_age_days":
        return 0 <= v < 30
    if col == "secs_link_to_pay":
        return v >= 0
    if col == "escalation_ratio":
        return v >= 2 and g("same_payee_count_24h", 0) >= 1
    if col in ("same_payee_count_24h", "same_payee_sum_24h"):
        return g("same_payee_count_24h", 0) >= 1
    if col == "note_risk":
        return v >= 0.5
    if col == "app_switches":
        return v >= 2
    if col == "typing_z":
        return v >= 1.5
    if col in ("pause_z", "pin_time_z"):
        return v >= 2
    if col == "failed_auth":
        return v >= 1
    if col.startswith("entry_"):
        return v == 1
    return False


class SatarkScorer:
    def __init__(self, model_path, thresholds_path=None):
        self.b = model_path if isinstance(model_path, dict) else joblib.load(model_path)
        self.cols = self.b["feature_columns"]
        self.tab_cols = self.b["tabular_columns"]
        self.thr = json.loads(Path(thresholds_path).read_text()) if thresholds_path else None

    def _note_risk(self, texts):
        return self.b["text_model"].predict_proba(self.b["text_vectorizer"].transform(texts))[:, 1]

    def _frame(self, feats, intents):
        """feats: list of dicts with the simulator feature names (+ entry_channel)."""
        numeric = [c for c in self.tab_cols if not c.startswith("entry_")]
        missing = sorted({c for f in feats for c in numeric if c not in f and c not in LINK_COLS})
        if missing:  # never silently fill defaults
            raise ValueError(f"Missing features from feature builder: {missing}")
        X = pd.DataFrame([{c: f.get(c, np.nan) for c in numeric} for f in feats])
        X[LINK_COLS] = X[LINK_COLS].astype(float).fillna(-1)
        for c in self.tab_cols:
            if c.startswith("entry_"):
                X[c] = [1 if f"entry_{f.get('entry_channel')}" == c else 0 for f in feats]
        X = X[self.tab_cols]
        X["note_risk"] = self._note_risk([INTENT_TEXT.get(i or "none", "") for i in intents])
        return X[self.cols]

    def _tier(self, s):
        if not self.thr:
            return None
        return "red" if s >= self.thr["red"] else "amber" if s >= self.thr["amber"] else "green"

    def score(self, features, note_intent="none", max_reasons=3):
        X = self._frame([features], [note_intent])
        s = float(self.b["fusion_model"].predict_proba(X)[:, 1][0])
        contrib = self.b["fusion_model"].get_booster().predict(xgb.DMatrix(X), pred_contribs=True)[0][:-1]
        row = X.iloc[0]
        reasons = []
        for i in np.argsort(-contrib):
            if contrib[i] <= 0 or len(reasons) >= max_reasons:
                break
            if not _is_risky(self.cols[i], row):
                continue
            code = REASON_MAP.get(self.cols[i])
            if code and code not in reasons:
                reasons.append(code)
        return {"fusion_score": s, "tier_hint": self._tier(s), "reasons": reasons}

    def score_frame(self, df, intents):
        """Batch scoring of a dataframe with the simulator feature columns. `intents` must be what the
        phone would send (keyword rules on the note text), never the simulator's note_intent label."""
        X = self._frame(df.to_dict("records"), list(intents))
        return self.b["fusion_model"].predict_proba(X)[:, 1]
