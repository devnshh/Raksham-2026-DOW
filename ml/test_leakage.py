"""Leak tripwires (plan 1.3). ml/evaluate.py runs these first and refuses to score if any fails.

    PYTHONPATH=. python -m pytest ml/test_leakage.py -q
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from worlds import (HOLDOUT_SEED, METADATA, MODELS, TRAIN_SEEDS, VALIDATION_SEEDS, live, phone_view,  # noqa: E402
                    world)
from validate_sim import check_point_in_time  # noqa: E402  (sim/, on the path via worlds)

from model_service.satark_scorer import SatarkScorer  # noqa: E402


@pytest.fixture(scope="module")
def bundle():
    return joblib.load(MODELS / "satark_model.joblib")


@pytest.fixture(scope="module")
def train():
    return live(world("train", TRAIN_SEEDS[0]))


@pytest.fixture(scope="module")
def holdout():
    return world("holdout", HOLDOUT_SEED)


def test_no_metadata_reaches_model_or_scorer(bundle, train):
    assert not set(bundle["feature_columns"]) & set(METADATA)
    inputs, _ = phone_view(train.head(5))
    assert not set(inputs.columns) & set(METADATA + ["note_text"])


def test_no_single_feature_leak_on_train(bundle, train):
    inputs, intents = phone_view(train)
    X = SatarkScorer(bundle)._frame(inputs.to_dict("records"), intents)
    y = train.is_scam.to_numpy()
    aucs = {c: roc_auc_score(y, X[c]) for c in X.columns if X[c].nunique() > 1}
    worst = max(aucs, key=lambda c: max(aucs[c], 1 - aucs[c]))
    assert max(aucs[worst], 1 - aucs[worst]) <= .95, f"{worst} alone has ROC-AUC {aucs[worst]:.3f}"


def test_train_and_holdout_share_no_rows(train, holdout):
    h = lambda d: set(pd.util.hash_pandas_object(d.drop(columns=["world"]), index=False))
    assert not h(world("train", TRAIN_SEEDS[0])) & h(holdout)


def test_holdout_features_are_point_in_time(holdout):
    bad = check_point_in_time(holdout, n=400)
    assert not bad, f"{len(bad)} of 400 holdout rows disagree with a recompute from prior rows"


def test_thresholds_and_model_never_used_the_holdout():
    thr = json.loads((MODELS / "thresholds.json").read_text())
    assert thr["set_on"]["world"] == "validation"
    assert set(thr["set_on"]["seeds"]) <= set(VALIDATION_SEEDS)
    man = json.loads((MODELS / "manifest.json").read_text())
    assert set(man["train_seeds"]) <= set(TRAIN_SEEDS)
    assert HOLDOUT_SEED not in man["train_seeds"] + man["validation_seeds"] + thr["set_on"]["seeds"]
    assert not set(man["train_seeds"]) & set(man["validation_seeds"])


def test_world_roles_cannot_be_swapped():
    with pytest.raises(ValueError):
        world("validation", HOLDOUT_SEED)
    with pytest.raises(ValueError):
        world("train", HOLDOUT_SEED)
    assert np.isin(HOLDOUT_SEED, TRAIN_SEEDS + VALIDATION_SEEDS).sum() == 0
