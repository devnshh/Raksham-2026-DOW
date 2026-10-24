"""World roles, loading, and the payment-time view of a row. Shared by train, leak tests and evaluation.

Roles are fixed (plan "Honesty rules"): the model fits on the train world only, thresholds and any
choice between models use validation worlds only, and the holdout world is scored only to report.
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "sim"
DATA = SIM / "data"
MODELS = ROOT / "model_service" / "models"
for p in (str(ROOT), str(SIM)):
    if p not in sys.path:
        sys.path.insert(0, p)

from satark_sim import FEATURES, generate  # noqa: E402
from api.policy.intent import resolve_note_intent  # noqa: E402

TRAIN_SEEDS = (11,)
VALIDATION_SEEDS = (33,)
HOLDOUT_SEED = 22
USERS = 5000

# Simulator metadata: labels and identifiers that must never reach the model or the scorer (plan rule 5).
METADATA = ["is_scam", "scenario", "variant", "journey_id", "step", "hard_negative", "warmup", "note_intent",
            "user_id", "payee_id", "event_id", "world"]
# What the scorer may see: the simulator's feature columns. The note text itself never leaves the phone;
# only its keyword intent does (see phone_view).
INPUTS = [c for fam in FEATURES.values() for c in fam if c != "note_text"]
# Not measured at risk-check time: the phone sends device_new=false and failed_auth=0, and the check runs
# before the PIN screen, so there is no PIN time (risk-sdk RealSignalSource.kt, api/routers/assess.py).
NOT_MEASURED = {"device_new": 0, "failed_auth": 0, "pin_time_z": 0.0}


def world(role, seed, users=USERS):
    """Generates (or loads the cached copy of) one world. 'train' oversamples victims; every other role has
    realistic prevalence. A seed belongs to exactly one role."""
    fixed = {**{s: "train" for s in TRAIN_SEEDS}, **{s: "validation" for s in VALIDATION_SEEDS}, HOLDOUT_SEED: "holdout"}
    if fixed.get(seed, "fresh") != role:
        raise ValueError(f"seed {seed} is the {fixed.get(seed, 'fresh')} world, not {role}")
    path = DATA / f"{role}_seed{seed}_u{users}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    df = generate("train" if role == "train" else "test", seed, users)
    df["world"] = role
    DATA.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


def live(df):
    """Rows after the warm-up period (scams only start after it)."""
    return df[df.warmup == 0].reset_index(drop=True)


def phone_view(df):
    """Inputs exactly as the phone and server have them at payment time, plus the note intent the phone
    would send (keyword rules on the note text, never the simulator's note_intent label)."""
    X = df[INPUTS].assign(**NOT_MEASURED)
    intents = [resolve_note_intent(None, t) for t in df.note_text]
    return X, intents


def data_hash(df):
    """Order-sensitive hash of a world's rows, ignoring the role column."""
    h = pd.util.hash_pandas_object(df.drop(columns=["world"]), index=False).to_numpy()
    return hashlib.sha256(h.tobytes()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
