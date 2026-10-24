#!/usr/bin/env python3
"""Train the Satark model on the train world and set its thresholds on the validation world.

    python ml/train.py

Writes model_service/models/satark_model.joblib, thresholds.json and manifest.json. The holdout world is
never loaded here.
"""
import json
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))
from worlds import (FEATURES, HOLDOUT_SEED, MODELS, ROOT, TRAIN_SEEDS, USERS, VALIDATION_SEEDS,  # noqa: E402
                    data_hash, file_hash, live, phone_view, world)

from model_service.satark_scorer import SatarkScorer  # noqa: E402

ENTRY = ["contact", "deep_link_sms", "deep_link_whatsapp", "merchant_collect", "qr_gallery", "qr_scan", "typed_vpa"]
TABULAR = [c for fam in FEATURES.values() for c in fam if c not in ("entry_channel", "note_text")] + [f"entry_{e}" for e in ENTRY]
# Alert budgets for the thresholds, fixed before training: red on 0.03% and amber on 0.1% of payments.
BUDGET = {"red": .0003, "amber": .001}
SEED = 42


def fit_bundle(tr):
    """Fits the note model and the fusion model on train-world rows. The fusion model sees note_risk
    exactly as served: note text -> keyword intent -> representative text -> note model."""
    assert set(tr.world) == {"train"}, "the model fits on the train world only"
    y = tr.is_scam.to_numpy()
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3, dtype=np.float32)
    text = LogisticRegression(max_iter=1000, C=2, random_state=SEED).fit(vec.fit_transform(tr.note_text), y)
    bundle = dict(text_vectorizer=vec, text_model=text, tabular_columns=TABULAR, feature_columns=TABULAR + ["note_risk"],
                  entry_categories=ENTRY, target="is_scam", feature_families=FEATURES, seed=SEED,
                  model_description="Character n-gram TF-IDF + Logistic Regression note-risk score, combined with "
                                    "simulator tabular features using XGBoost (ml/train.py)")
    inputs, intents = phone_view(tr)
    X = SatarkScorer(bundle)._frame(inputs.to_dict("records"), intents)
    bundle["fusion_model"] = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=.1, subsample=.8, colsample_bytree=.8,
        scale_pos_weight=(y == 0).sum() / max(1, (y == 1).sum()), eval_metric="logloss",
        random_state=SEED, n_jobs=-1, verbosity=0).fit(X, y)
    return bundle


def set_thresholds(bundle, va):
    """Raw score cut-offs at the alert budgets, on validation-world rows only."""
    assert set(va.world) == {"validation"}, "thresholds are set on a validation world only"
    inputs, intents = phone_view(va)
    s = SatarkScorer(bundle).score_frame(inputs, intents)
    return {k: float(np.quantile(s, 1 - b)) for k, b in BUDGET.items()}


def git_commit():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main():
    assert HOLDOUT_SEED not in TRAIN_SEEDS + VALIDATION_SEEDS
    tr = pd.concat([live(world("train", s)) for s in TRAIN_SEEDS], ignore_index=True)
    bundle = fit_bundle(tr)
    model_path = MODELS / "satark_model.joblib"
    joblib.dump(bundle, model_path)

    va = live(world("validation", VALIDATION_SEEDS[0]))
    thr = set_thresholds(bundle, va)
    thr.update(set_on={"world": "validation", "seeds": list(VALIDATION_SEEDS[:1]), "users": USERS},
               note="Raw score cut-offs set on a separate validation world (simulator seed "
                    f"{VALIDATION_SEEDS[0]}, realistic prevalence) at alert budgets red 0.03% / amber 0.1%. "
                    f"The holdout world (seed {HOLDOUT_SEED}) was not used. Simulation only; not calibrated probabilities.")
    (MODELS / "thresholds.json").write_text(json.dumps(thr, indent=2) + "\n")

    manifest = {
        "train_seeds": list(TRAIN_SEEDS), "validation_seeds": list(VALIDATION_SEEDS[:1]), "users_per_world": USERS,
        "train_rows": len(tr), "train_scam_rows": int(tr.is_scam.sum()), "train_data_sha256": data_hash(tr),
        "validation_rows": len(va), "validation_scam_rows": int(va.is_scam.sum()),
        "feature_columns": bundle["feature_columns"], "model_sha256": file_hash(model_path),
        "git_commit": git_commit(), "scikit_learn": sklearn.__version__, "xgboost": xgboost.__version__,
        "note": "Rows after the 30-day warm-up. Features not measured at risk-check time (device_new, failed_auth, "
                "pin_time_z) are zero in training, as in production.",
    }
    (MODELS / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    va_y = va.is_scam.to_numpy()
    print(f"trained on {len(tr):,} rows ({int(tr.is_scam.sum())} scams); thresholds amber {thr['amber']:.4f} "
          f"red {thr['red']:.4f} on {len(va):,} validation rows ({int(va_y.sum())} scams)")


if __name__ == "__main__":
    main()
