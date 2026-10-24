#!/usr/bin/env python3
"""Robustness (plan 1.5, assumption A6): key simulator rates at half and double.

    python ml/robustness.py              # seed 101, 5,000 users, about 10 minutes

Every variant is the same unused seed with one rate changed, so only that rate differs between runs.
The model and thresholds are the deployed ones and are not re-tuned: this shows how recall and the
alert rate move when an assumption is wrong. The holdout world is not used.
"""
import argparse
import contextlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import LEVELS, RESULTS, model_tier, replay_policy, report, run_leak_tripwires  # noqa: E402
from worlds import HOLDOUT_SEED, MODELS, ROOT, TRAIN_SEEDS, VALIDATION_SEEDS, phone_view  # noqa: E402

import satark_sim  # noqa: E402
from model_service.satark_scorer import SatarkScorer  # noqa: E402


def _on_call_mean(f):
    """Beta(a, b) for legit payments made on a call, with its mean scaled by f and b kept."""
    a, b = satark_sim.P["legit_on_call"][0]
    m = f * a / (a + b)
    return (m * b / (1 - m), b)


def _callers_saved(f, scam):
    """Scales the saved-contact share of scam callers (scam=True) or of legit callers, capped at 1."""
    rates = dict(satark_sim.P["caller_in_contacts"][0])
    keys = ("scam", "task_scam", "investment", "fake_qr") if scam else ("legit", "new_individual", "new_tenancy",
                                                                       "item_purchase", "emergency")
    return {**rates, **{k: min(1.0, rates[k] * f) for k in keys}}


# Rates the plan's assumption A6 names as most likely to be wrong, and how to scale each.
KNOBS = {
    "genuine callers who are saved contacts": ("caller_in_contacts", lambda f: _callers_saved(f, scam=False)),
    "scam callers who are saved contacts": ("caller_in_contacts", lambda f: _callers_saved(f, scam=True)),
    "legit payments made on a call": ("legit_on_call", _on_call_mean),
    "scam journeys that use an evasion": ("evasive_share", lambda f: satark_sim.P["evasive_share"][0] * f),
    "victims who report the scam": ("report_prob", lambda f: min(1.0, satark_sim.P["report_prob"][0] * f)),
    "new payers per day into an active mule": ("mule_new_payers", lambda f: tuple(v * f for v in satark_sim.P["mule_new_payers"][0])),
}


@contextlib.contextmanager
def rate(key, value):
    old = satark_sim.P[key]
    satark_sim.P[key] = (value, old[1])
    try:
        yield
    finally:
        satark_sim.P[key] = old


def score(df, scorer):
    inputs, intents = phone_view(df)
    s = scorer.score_frame(inputs, intents)
    policy, _ = replay_policy(df, inputs, intents, s, scorer.thr)
    keep = (df.warmup == 0).to_numpy()
    d = df[keep].reset_index(drop=True)
    model = np.array([model_tier(x, scorer.thr) for x in s[keep]], dtype=object)
    summary = {}
    for name, tiers in (("model_only", model), ("model_plus_policy", policy[keep])):
        r = report(d, tiers)
        summary[name] = {lvl: {k: r[lvl][k] for k in ("recall", "precision", "alerts_per_1000", "false_positive_rate")}
                         for lvl in LEVELS}
    return {"payments": len(d), "scam_payments": int(d.is_scam.sum()), **summary}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=101)
    ap.add_argument("--users", type=int, default=5000)
    a = ap.parse_args()
    if a.seed in (*TRAIN_SEEDS, *VALIDATION_SEEDS, HOLDOUT_SEED):
        ap.error("use a seed that is not the train, validation or holdout world")
    run_leak_tripwires()
    scorer = SatarkScorer(str(MODELS / "satark_model.joblib"), str(MODELS / "thresholds.json"))

    runs = {"baseline": score(satark_sim.generate("test", a.seed, a.users).assign(world="robustness"), scorer)}
    print("baseline", runs["baseline"]["model_plus_policy"]["warning"], flush=True)
    for label, (key, scale) in KNOBS.items():
        for f, tag in ((0.5, "half"), (2.0, "double")):
            with rate(key, scale(f)):
                df = satark_sim.generate("test", a.seed, a.users).assign(world="robustness")
            runs[f"{label}: {tag}"] = score(df, scorer)
            print(f"{label}: {tag}", runs[f"{label}: {tag}"]["model_plus_policy"]["warning"], flush=True)

    out = {"seed": a.seed, "users": a.users, "thresholds": {k: scorer.thr[k] for k in ("amber", "red")},
           "note": "Same seed for every variant, one rate changed at a time; deployed model and thresholds, not "
                   "re-tuned. Changing a rate also shifts the simulator's later random draws, so part of each "
                   "difference is chance. Simulation results, not real-world accuracy.", "runs": runs}
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"robustness_seed{a.seed}_u{a.users}.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
