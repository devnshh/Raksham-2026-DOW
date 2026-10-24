#!/usr/bin/env python3
"""Score a world through the production path and report the plan 1.5 metrics.

    python ml/evaluate.py --holdout                            # the logged holdout run
    python ml/evaluate.py --role validation --seed 33          # for choosing; never logged
    python ml/evaluate.py --role fresh --seed 1234 --users 300 # a judge-picked unseen world

Every row is scored by SatarkScorer with only what the phone and server have at payment time, then
replayed through the production PolicyEngine in time order per user. The leak tripwires run first.
Each holdout run is appended to ml/eval_log.md; the last logged run is the number we report.
"""
import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from worlds import (HOLDOUT_SEED, MODELS, ROOT, TRAIN_SEEDS, USERS, VALIDATION_SEEDS, file_hash,  # noqa: E402
                    live, phone_view, world)

from api.config import POLICY_FILE_PATH  # noqa: E402
from api.policy.engine import PolicyEngine  # noqa: E402
from model_service.satark_scorer import SatarkScorer  # noqa: E402
from satark_sim import DAY, SCEN  # noqa: E402

ML = Path(__file__).resolve().parent
LOG = ML / "eval_log.md"
RESULTS = ML / "results"
LEVELS = {"warning": ("amber", "red"), "red": ("red",)}  # warning = any amber or red screen
SLICES = ["age_band", "language", "device_tier", "assistive_tech"]


class _Replay:
    """Hands the PolicyEngine the batch SatarkScorer score of the row being replayed."""

    def __init__(self, scores, thr):
        self.scores, self.thr, self.i = scores, thr, 0

    def score(self, features, note_intent="none"):
        s = float(self.scores[self.i])
        return {"fusion_score": s, "tier_hint": model_tier(s, self.thr), "reasons": []}


def model_tier(s, thr):
    return "red" if s >= thr["red"] else "amber" if s >= thr["amber"] else "green"


def replay_policy(df, inputs, intents, scores, thr):
    """Production tier and deciding rule per row, in time order. Every simulated payment counts as completed
    (the simulator's later features assume it happened), so it feeds trusted-payee history; every amber
    shown counts towards that user's 7-day cap, as cases do in production."""
    replay = _Replay(scores, thr)
    engine = PolicyEngine(POLICY_FILE_PATH, scorer=replay)
    recs = inputs.to_dict("records")
    ts, users, payees = df.ts.to_numpy(), df.user_id.to_numpy(), df.payee_id.to_numpy()
    history, ambers = {}, defaultdict(deque)
    tiers, rules = np.empty(len(df), dtype=object), np.empty(len(df), dtype=object)
    for i in np.lexsort((users, ts)):
        f = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in recs[i].items()}
        f["note_intent"] = intents[i]
        key = (users[i], payees[i])
        h = history.get(key)
        cap = ambers[users[i]]
        while cap and cap[0] < ts[i] - 7 * DAY:
            cap.popleft()
        replay.i = i
        d = engine.evaluate(f, is_confirmed_scam_payee=False, user_amber_count_7d=len(cap),
                            trusted_payee_history=(h[0], int((h[2] - h[1]) / DAY)) if h else None)
        tiers[i], rules[i] = d.tier, d.applied_rules[-1]
        if d.tier == "amber":
            cap.append(ts[i])
        history[key] = (h[0] + 1, h[1], ts[i]) if h else (1, ts[i], ts[i])
    return tiers, rules


def confusion(y, alert):
    tp, fp = int((alert & y).sum()), int((alert & ~y).sum())
    fn, tn = int((~alert & y).sum()), int((~alert & ~y).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None, "false_positive_rate": fp / (fp + tn) if fp + tn else None,
            "alerts_per_1000": 1000 * float(alert.mean())}


def rate(x):
    return float(x.mean()) if len(x) else None


def report(df, tiers):
    """Metrics for one version (model only, or model plus policy)."""
    y = df.is_scam.to_numpy() == 1
    out = {}
    for level, shown in LEVELS.items():
        alert = np.isin(tiers, shown)
        scam = df[y].assign(hit=alert[y])
        legit = df[~y].assign(hit=alert[~y])
        out[level] = {
            **confusion(y, alert),
            "journeys_interrupted": rate(scam.groupby("journey_id").hit.any()),
            "recall_by_scenario": {s: rate(g.hit) for s, g in scam.groupby("scenario")},
            "recall_evasive": rate(scam[scam.variant != ""].hit), "recall_plain": rate(scam[scam.variant == ""].hit),
            "recall_by_evasion": {v: rate(g.hit) for v, g in scam[scam.variant != ""].groupby("variant")},
            "false_alarm_rate_by_group": {c: {str(k): rate(g.hit) for k, g in legit.groupby(c)} for c in SLICES},
        }
    return out


def failures(df, inputs, intents, policy, rules, scorer, n_examples=3):
    """Missed scams and false alarms of the deployed version (model plus policy, any warning)."""
    y = df.is_scam.to_numpy() == 1
    alert = np.isin(policy, LEVELS["warning"])

    def examples(idx):
        rows = []
        for i in idx[:n_examples]:
            f = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in inputs.iloc[i].items()}
            r = df.iloc[i]
            rows.append({"event_id": int(r.event_id), "scenario": r.scenario, "variant": r.variant,
                         "tags": r.hard_negative, "amount": float(r.amount), "entry": r.entry_channel,
                         "note_intent_sent": intents[i], "on_call": int(r.on_call), "payee_first_time": int(r.payee_first_time),
                         "payee_age_days": round(float(r.payee_age_days), 1), "fan_in_24h": int(r.payee_new_payers_24h),
                         "reports": int(r.payee_reports_prior), "amount_ratio": round(float(r.amount_ratio), 2),
                         "deciding_rule": rules[i], "tier": policy[i],
                         "model_reasons": scorer.score(f, note_intent=intents[i])["reasons"]})
        return rows

    missed = df[y & ~alert]
    groups = missed.assign(rule=rules[y & ~alert]).groupby(["scenario", "variant", "rule"]).size()
    top_missed = []
    for (sc, var, rule), n in groups.sort_values(ascending=False).head(6).items():
        idx = np.flatnonzero(y & ~alert & (df.scenario == sc).to_numpy() & (df.variant == var).to_numpy() & (rules == rule))
        top_missed.append({"scenario": sc, "variant": var or "plain", "deciding_rule": rule, "payments": int(n),
                           "examples": examples(idx)})

    fa = df[~y & alert].assign(rule=rules[~y & alert])
    tags = fa.hard_negative.replace("", "none").str.split("|").explode()
    top_false = []
    for tag, n in tags.value_counts().head(6).items():
        has = df.hard_negative.replace("", "none").str.split("|").apply(lambda t: tag in t).to_numpy()
        idx = np.flatnonzero(~y & alert & has)
        top_false.append({"tag": tag, "false_alarms": int(n), "share_of_false_alarms": n / max(1, len(fa)),
                          "false_alarm_rate_in_tag": rate(alert[~y & has]), "examples": examples(idx)})

    def tag_rate(tag, extra=None):
        has = df.hard_negative.str.contains(tag, regex=False).to_numpy() & ~y
        if extra is not None:
            has &= extra
        return {"payments": int(has.sum()), "false_alarm_rate": rate(alert[has])}

    expected = {  # the failure cases the plan expects; measured, not assumed
        "rent to a new landlord while on a call": tag_rate("new_tenancy_rent", df.on_call.to_numpy() == 1),
        "screen-reader users": tag_rate("assistive_user"),
        "all legit payments": {"payments": int((~y).sum()), "false_alarm_rate": rate(alert[~y])},
        "scams with no call, unreported payee, normal amount": {
            "payments": int((m := y & (df.on_call.to_numpy() == 0) & (df.payee_reports_prior.to_numpy() == 0)
                             & (df.amount_ratio.to_numpy() < 2)).sum()), "recall": rate(alert[m])},
    }
    return {"top_missed": top_missed, "top_false_alarms": top_false, "expected_cases": expected,
            "deciding_rule_of_missed_scams": {k: int(v) for k, v in missed.assign(rule=rules[y & ~alert]).rule.value_counts().items()}}


def leave_one_scenario_out(te):
    """Unseen scam types: refit without one scenario's scam rows (train world), set the warning threshold
    on the validation world, and measure that scenario's recall on the evaluated world (model only)."""
    from train import BUDGET, fit_bundle  # noqa: E402
    tr = live(world("train", TRAIN_SEEDS[0]))
    va_inputs, va_intents = phone_view(live(world("validation", VALIDATION_SEEDS[0])))
    out = {}
    for sc in SCEN:
        b = fit_bundle(tr[(tr.is_scam == 0) | (tr.scenario != sc)])
        s = SatarkScorer(b)
        thr = float(np.quantile(s.score_frame(va_inputs, va_intents), 1 - BUDGET["amber"]))
        rows = te[te.scenario == sc]
        if len(rows):
            out[sc] = rate(s.score_frame(*phone_view(rows)) >= thr)
        print(f"  left out {sc}: recall {out.get(sc)}", flush=True)
    return out


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def log_holdout_run(res, path):
    if not LOG.exists():
        LOG.write_text(
            "# Holdout evaluation log\n\n"
            f"Every scoring of the holdout world (simulator seed {HOLDOUT_SEED}) is appended here by `ml/evaluate.py "
            "--holdout`, and the last row is the number we report. Never re-run to pick a better result.\n\n"
            "Before this log: the simulator's own `validate_sim.py` realism checks scored the seed-22 world with a "
            "throwaway model to validate the generator, and the earlier model bundle's training history is not "
            "recorded in this repo. Run 1 is the first holdout run of a model built by `ml/train.py`.\n\n"
            "Simulation results on an unseen synthetic world, not real-world accuracy. Warning = amber or red screen.\n\n"
            "| Run | Date (UTC) | Commit | Model sha256 | Thresholds sha256 | Model only: warning P / R | "
            "Model + policy: warning P / R / per 1,000 | Model + policy: red P / R | Results |\n"
            "|---|---|---|---|---|---|---|---|---|\n")
    pct = lambda v: "n/a" if v is None else f"{100 * v:.1f}%"
    m, p = res["model_only"], res["model_plus_policy"]
    row = (f"| {res['holdout_run']} | {res['date']} | {res['git_commit'][:10]} | {res['model_sha256'][:12]} | "
           f"{res['thresholds_sha256'][:12]} | {pct(m['warning']['precision'])} / {pct(m['warning']['recall'])} | "
           f"{pct(p['warning']['precision'])} / {pct(p['warning']['recall'])} / {p['warning']['alerts_per_1000']:.2f} | "
           f"{pct(p['red']['precision'])} / {pct(p['red']['recall'])} | `{path.relative_to(ROOT)}` |\n")
    lines = LOG.read_text().splitlines(keepends=True)
    lines.insert(max(i for i, ln in enumerate(lines) if ln.startswith("|")) + 1, row)  # end of the table
    LOG.write_text("".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--holdout", action="store_true", help="the logged holdout run")
    ap.add_argument("--role", choices=["validation", "fresh"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--users", type=int, default=USERS)
    ap.add_argument("--no-loso", action="store_true", help="skip the leave-one-scenario-out refits")
    a = ap.parse_args()
    role, seed = ("holdout", HOLDOUT_SEED) if a.holdout else (a.role, a.seed)
    if role is None or seed is None:
        ap.error("pass --holdout, or --role and --seed")

    if a.holdout:
        dirty = [ln for ln in git("status", "--porcelain").splitlines()
                 if not ln[3:].startswith(("ml/results", "ml/eval_log.md", "plan.md"))]
        if dirty:
            sys.exit("Commit first: the log records the commit that produced the numbers.\n" + "\n".join(dirty))
    leak = subprocess.run([sys.executable, "-m", "pytest", "-q", str(ML / "test_leakage.py")], cwd=ROOT,
                          env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True)
    print(leak.stdout.strip().splitlines()[-1])
    if leak.returncode:
        sys.exit("Leak tripwire failed; not scoring.\n" + leak.stdout)

    full = world(role, seed, a.users)
    thr_path, model_path = MODELS / "thresholds.json", MODELS / "satark_model.joblib"
    scorer = SatarkScorer(str(model_path), str(thr_path))
    inputs, intents = phone_view(full)
    scores = scorer.score_frame(inputs, intents)
    policy, rules = replay_policy(full, inputs, intents, scores, scorer.thr)
    keep = (full.warmup == 0).to_numpy()
    df, scores, policy, rules = full[keep].reset_index(drop=True), scores[keep], policy[keep], rules[keep]
    inputs, intents = inputs[keep].reset_index(drop=True), [t for t, k in zip(intents, keep) if k]
    model = np.array([model_tier(s, scorer.thr) for s in scores], dtype=object)

    n_prev = sum(1 for ln in LOG.read_text().splitlines() if ln.startswith("| ") and ln[2].isdigit()) if LOG.exists() else 0
    res = {
        "role": role, "seed": seed, "users": a.users, "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "git_commit": git("rev-parse", "HEAD"), "model_sha256": file_hash(model_path), "thresholds_sha256": file_hash(thr_path),
        "thresholds": {k: scorer.thr[k] for k in ("amber", "red")}, "payments": len(df), "scam_payments": int(df.is_scam.sum()),
        "scam_journeys": int(df[df.is_scam == 1].journey_id.nunique()),
        "holdout_run": n_prev + 1 if a.holdout else None,
        "note": "Simulation results on an unseen synthetic world, not real-world accuracy." if role != "validation" else
                "Validation world: thresholds were set on this world, so these numbers are optimistic.",
        "model_only": report(df, model), "model_plus_policy": report(df, policy),
        "failures": failures(df, inputs, intents, policy, rules, scorer),
    }
    if not a.no_loso and role != "fresh":
        print("leave-one-scenario-out refits:", flush=True)
        res["unseen_scam_types_recall"] = leave_one_scenario_out(df)

    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / (f"holdout_run{res['holdout_run']}.json" if a.holdout else f"{role}_seed{seed}_u{a.users}.json")
    path.write_text(json.dumps(res, indent=2, default=str) + "\n")
    if a.holdout:
        log_holdout_run(res, path)
    for version in ("model_only", "model_plus_policy"):
        for level in LEVELS:
            r = res[version][level]
            print(f"{version:18} {level:7} precision {r['precision'] or 0:.3f} recall {r['recall'] or 0:.3f} "
                  f"FPR {r['false_positive_rate']:.5f} alerts/1000 {r['alerts_per_1000']:.2f} "
                  f"tp {r['tp']} fp {r['fp']} fn {r['fn']}")
    print(f"wrote {path.relative_to(ROOT)}" + (f"; logged as holdout run {res['holdout_run']}" if a.holdout else ""))


if __name__ == "__main__":
    main()
