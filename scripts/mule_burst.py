#!/usr/bin/env python3
"""
Demo journey 3 ("Mule caught"): many new payers pay one new payee within minutes.

    python scripts/mule_burst.py                       # 15 payers -> quickloan.agent@ybl, about a minute
    python scripts/mule_burst.py --payee x@ybl --payers 20 --gap 0

Each simulated payer goes through the app's own path: a risk check (POST /v1/risk/assess), then, if
the check allows it, POST /v1/payments/complete. Only completed payments count towards the payee's
fan-in, so the analyst console then shows the cluster. Payers whose check is red stay on hold and are
not completed, exactly as in the app.
"""

import argparse
import random
import secrets
import sys
import time

import httpx


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--payee", default="quickloan.agent@ybl")
    ap.add_argument("--payers", type=int, default=15)
    ap.add_argument("--gap", type=float, default=4.0, help="seconds between payers; the default spreads 15 payers over about a minute")
    a = ap.parse_args()
    if a.payers * a.gap > 600:
        ap.error("the burst must fit in 10 minutes")

    run = secrets.token_hex(2)  # fresh payer IDs each run, so they count as new payers again
    rng = random.Random()
    counts = {"completed": 0, "held": 0, "declined": 0}
    with httpx.Client(base_url=a.api, timeout=10) as http:
        for i in range(1, a.payers + 1):
            user = f"burst-{run}-{i:02d}@ybl"
            amount = float(rng.choice([1999, 2499, 2999, 4999, 7500, 9999]))
            r = http.post("/v1/risk/assess", json={
                "user_ref": user, "payee_vpa": a.payee, "amount": amount, "entry_channel": "typed_vpa",
                "session": {"on_call": rng.random() < .6, "app_switches": rng.randint(0, 3)},
                "context": {"note_intent": rng.choice(["none", "refund", "task"])},
            })
            r.raise_for_status()
            d = r.json()
            if d["tier"] == "decline":
                counts["declined"] += 1
            else:
                done = http.post("/v1/payments/complete", json={
                    "case_id": d["case_id"], "user_ref": user, "payee_vpa": a.payee, "amount": amount})
                if done.status_code == 409:
                    counts["held"] += 1
                else:
                    done.raise_for_status()
                    counts["completed"] += 1
            print(f"{i:2d}. {user} pays ₹{amount:,.0f}: {d['tier']}"
                  f"{' (on hold, not completed)' if d['tier'] == 'red' else ''}", flush=True)
            if i < a.payers:
                time.sleep(a.gap)
    print(f"\n{counts['completed']} completed, {counts['held']} held by a red pause, {counts['declined']} declined. "
          f"Open http://127.0.0.1:8000/console and look up {a.payee}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
