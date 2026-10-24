#!/usr/bin/env python3
"""Validate the Satark simulator output.

    python validate_sim.py [--data data]

HARD checks (exit 1 on failure): schema, determinism, point-in-time correctness, prevalence,
scenario coverage, hard negatives present, no single-feature leak.
REALISM checks (PASS or WARN): a fusion model trained on the train world and scored on the
test world must be neither trivial nor useless. The ranges in RANGES were fixed before the
first run, so the generator is judged against them rather than tuned to them.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import cross_val_predict
from xgboost import XGBClassifier

from satark_sim import DAY, EVASIONS, FEATURES, META, SCEN, generate

RANGES = {
    "test_prevalence": (1 / 10000, 1 / 1000),
    "train_prevalence": (1 / 500, 1 / 50),
    "legit_on_call_share": (.05, .15),
    "max_single_feature_auc": .95,
    "recall_at_budget": (.40, .95),     # alert budget = 0.1% of all payments
    "loso_median_recall": (.30, .97),   # at 1% false-positive rate, per held-out scam type
    "families_that_matter": 2,          # families whose removal costs > 0.02 PR-AUC
    "fairness_ratio": 3.0,              # worst group legit alert rate / overall legit alert rate
}
BUDGET = .001
LINK = ["link_bad", "link_domain_age_days", "secs_link_to_pay"]
fails, warns = [], []


def hard(name, ok, detail):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if not ok:
        fails.append(name)


def soft(name, ok, detail):
    print(f"[{'PASS' if ok else 'WARN'}] {name}: {detail}")
    if not ok:
        warns.append(name)


def numeric(df):
    cols = [c for fam in FEATURES.values() for c in fam if c not in ("entry_channel", "note_text")]
    X = df[cols].copy()
    X[LINK] = X[LINK].fillna(-1)
    return pd.concat([X, pd.get_dummies(df.entry_channel, prefix="entry", dtype=int)], axis=1)


def family_cols(X, fam):
    base = [c for c in FEATURES[fam] if c in X.columns]
    if fam == "C_context":
        base += [c for c in X.columns if c.startswith("entry_")] + ["note_risk"]
    return base


def fit(X, y):
    m = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=.1, subsample=.8, colsample_bytree=.8,
                      scale_pos_weight=(y == 0).sum() / max(1, (y == 1).sum()), n_jobs=-1, verbosity=0)
    return m.fit(X, y)


def check_point_in_time(df, n=400):
    df = df.sort_values(["ts", "user_id"], kind="stable")
    by_user = {u: g for u, g in df.groupby("user_id")}
    sample = df[df.warmup == 0].sample(n, random_state=0)
    bad = []
    for r in sample.itertuples():
        prior = by_user[r.user_id]
        prior = prior[prior.ts < r.ts]
        same = prior[prior.payee_id == r.payee_id]
        expect_first = int(len(same) == 0)
        expect_24h = int((same.ts >= r.ts - DAY).sum())
        expect_esc = r.amount / same.amount.iloc[-1] if len(same) else 1.0
        p90 = prior[prior.ts >= r.ts - 90 * DAY].amount
        checks = [r.payee_first_time == expect_first, r.same_payee_count_24h == expect_24h,
                  np.isclose(r.escalation_ratio, expect_esc)]
        if len(p90) >= 5:
            checks.append(np.isclose(r.amount_ratio, r.amount / p90.median()))
        if not all(checks):
            bad.append(r.event_id)
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(Path(__file__).parent / "data"))
    a = ap.parse_args()
    tr_all = pd.read_parquet(Path(a.data) / "train.parquet")
    te_all = pd.read_parquet(Path(a.data) / "test.parquet")
    tr, te = tr_all[tr_all.warmup == 0].reset_index(drop=True), te_all[te_all.warmup == 0].reset_index(drop=True)

    print("== HARD CHECKS ==")
    feat_cols = [c for fam in FEATURES.values() for c in fam]
    missing = [c for c in META + feat_cols if c not in tr.columns]
    hard("schema", not missing, f"missing={missing}" if missing else f"{len(META)} meta + {len(feat_cols)} feature columns")
    non_link = [c for c in feat_cols if c not in LINK]
    nan_cols = [c for c in non_link if tr_all[c].isna().any() or te_all[c].isna().any()]
    is_link = tr_all.entry_channel.str.startswith("deep_link")
    link_ok = tr_all.loc[is_link, LINK].notna().all().all() and tr_all.loc[~is_link, LINK].isna().all().all()
    hard("no unexpected NaN", not nan_cols and link_ok, f"NaN in {nan_cols}" if nan_cols else "link fields set only for deep links")

    h = lambda d: pd.util.hash_pandas_object(d.drop(columns=["world"]), index=False).sum()
    same_seed = h(generate("test", 5, 150)) == h(generate("test", 5, 150))
    diff_seed = h(generate("test", 5, 150)) != h(generate("test", 6, 150))
    hard("determinism", same_seed and diff_seed, "same seed identical, different seed differs")

    dup = int(te_all.duplicated(["user_id", "ts"]).sum() + tr_all.duplicated(["user_id", "ts"]).sum())
    hard("unique user timestamps", dup == 0, f"{dup} payments share a timestamp with another payment by the same user")
    bad = check_point_in_time(te_all)
    hard("point-in-time features", not bad, f"{len(bad)} of 400 sampled rows disagree with a recompute from raw history")

    for name, d in (("test", te), ("train", tr)):
        rate = d.is_scam.mean()
        lo, hi = RANGES[f"{name}_prevalence"]
        hard(f"{name} prevalence", lo <= rate <= hi, f"1 in {1 / rate:,.0f} (allowed 1 in {1 / hi:,.0f} to 1 in {1 / lo:,.0f})")

    counts = tr[tr.is_scam == 1].scenario.value_counts()
    low = {s: int(counts.get(s, 0)) for s in SCEN if counts.get(s, 0) < 100}
    hard("scenario coverage (train)", not low, f"under 100 payments: {low}" if low else dict(counts))
    ev = tr[tr.is_scam == 1].groupby("variant").journey_id.nunique()
    low = {v: int(ev.get(v, 0)) for v in EVASIONS if ev.get(v, 0) < 3}
    hard("evasion coverage (train)", not low, f"under 3 journeys: {low}" if low else dict(ev.drop("", errors="ignore")))

    lg = te[te.is_scam == 0]
    tags = lg.hard_negative.str.split("|").explode().value_counts()
    need = {"emergency": 20, "item_purchase": 50, "new_tenancy_rent": 5, "device_change": 20, "legit_link": 1000,
            "qr_gallery_legit": 200, "assistive_user": 100, "remote_app_user": 50, "brandlike_shop": 50, "new_shop": 200}
    short = {k: int(tags.get(k, 0)) for k, v in need.items() if tags.get(k, 0) < v}
    hard("hard-negative tags present (test)", not short, f"short: {short}" if short else "all present")
    on_call = lg.on_call.mean()
    lo, hi = RANGES["legit_on_call_share"]
    hard("legit payments on a call", lo <= on_call <= hi, f"{on_call:.1%} of legit payments")
    risky = {
        "first-time payee at 5x usual amount": int(((lg.payee_first_time == 1) & (lg.amount_ratio >= 5)).sum()),
        "unverified payee with 5+ new payers in 24 h": int(((lg.payee_verified == 0) & (lg.payee_new_payers_24h >= 5)).sum()),
        "scam-like words in note": int(lg.note_text.str.contains("refund|token|advance|urgent", case=False).sum()),
    }
    hard("legit rows that look risky", min(risky.values()) >= 100, str(risky))

    y = tr.is_scam.values
    X = numeric(tr)
    aucs = {c: roc_auc_score(y, X[c]) for c in X.columns if X[c].nunique() > 1}
    aucs = {c: max(v, 1 - v) for c, v in aucs.items()}
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3)
    T = vec.fit_transform(tr.note_text)
    tr["note_risk"] = cross_val_predict(LogisticRegression(max_iter=1000, C=2), T, y, cv=5, method="predict_proba")[:, 1]
    aucs["note_text (char n-gram model)"] = roc_auc_score(y, tr.note_risk)
    top = sorted(aucs.items(), key=lambda kv: -kv[1])[:5]
    hard("no single-feature leak (train)", top[0][1] < RANGES["max_single_feature_auc"],
         ", ".join(f"{c} {v:.3f}" for c, v in top))

    print("\n== REALISM CHECKS ==")
    te["note_risk"] = LogisticRegression(max_iter=1000, C=2).fit(T, y).predict_proba(vec.transform(te.note_text))[:, 1]
    Xtr, Xte = numeric(tr), numeric(te)
    Xtr["note_risk"], Xte["note_risk"] = tr.note_risk, te.note_risk
    Xte = Xte.reindex(columns=Xtr.columns, fill_value=0)
    rng = np.random.default_rng(0)
    keep = (y == 1) | (rng.random(len(y)) < .35)  # subsample legit rows to keep fits fast
    model = fit(Xtr[keep], y[keep])
    s = model.predict_proba(Xte)[:, 1]
    yt = te.is_scam.values
    thr = np.quantile(s, 1 - BUDGET)
    flag = s >= thr
    rec, prauc = flag[yt == 1].mean(), average_precision_score(yt, s)
    lo, hi = RANGES["recall_at_budget"]
    soft("fusion recall at 0.1% alert budget (test)", lo <= rec <= hi,
         f"{rec:.2f} (range {lo}-{hi}); precision {yt[flag].mean():.2f}; PR-AUC {prauc:.3f}")
    per = te[yt == 1].assign(hit=flag[yt == 1]).groupby("scenario").hit.agg(["mean", "size"])
    print("        per scenario:", ", ".join(f"{k} {r['mean']:.2f} (n={r['size']})" for k, r in per.iterrows()))
    ev_hit = te[yt == 1].assign(hit=flag[yt == 1]).groupby(te[yt == 1].variant.ne("")).hit.mean()
    soft("evasive journeys are harder", ev_hit.get(True, 0) <= ev_hit.get(False, 1),
         f"evasive {ev_hit.get(True, float('nan')):.2f} vs plain {ev_hit.get(False, float('nan')):.2f}")

    drops = {}
    for fam in FEATURES:
        cols = [c for c in Xtr.columns if c not in family_cols(Xtr, fam)]
        m = fit(Xtr.loc[keep, cols], y[keep])
        drops[fam] = prauc - average_precision_score(yt, m.predict_proba(Xte[cols])[:, 1])
    n_matter = sum(v > .02 for v in drops.values())
    soft("signal families all contribute", n_matter >= RANGES["families_that_matter"],
         "PR-AUC drop when removed: " + ", ".join(f"{k} {v:+.3f}" for k, v in drops.items()))

    hold = (tr.user_id % 5 == 0).values
    loso = {}
    for sc in SCEN:
        tr_idx = keep & ~hold & ((y == 0) | (tr.scenario != sc).values)
        m = fit(Xtr[tr_idx], y[tr_idx])
        legit_hold = hold & (y == 0)
        t1 = np.quantile(m.predict_proba(Xtr[legit_hold])[:, 1], .99)
        loso[sc] = (m.predict_proba(Xtr[(tr.scenario == sc).values])[:, 1] >= t1).mean()
    med = float(np.median(list(loso.values())))
    lo, hi = RANGES["loso_median_recall"]
    soft("unseen scam types (leave-one-scenario-out, train)", lo <= med <= hi,
         f"median recall {med:.2f} at 1% FPR; " + ", ".join(f"{k} {v:.2f}" for k, v in loso.items()))

    lf = flag[yt == 0]
    overall = max(lf.mean(), 1e-9)
    groups = {f"age {g}": lf[(te.age_band == g).values[yt == 0]].mean() for g in sorted(te.age_band.unique())}
    groups["assistive"] = lf[(te.assistive_tech == 1).values[yt == 0]].mean()
    worst = max(groups.values()) / overall
    soft("fairness of legit alerts", worst <= RANGES["fairness_ratio"],
         f"worst group {worst:.1f}x overall; " + ", ".join(f"{k} {v:.3%}" for k, v in groups.items()))

    print(f"\n{len(fails)} hard failures, {len(warns)} warnings")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
