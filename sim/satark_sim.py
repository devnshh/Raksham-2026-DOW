#!/usr/bin/env python3
"""Satark scenario simulator.

Synthetic UPI payment sessions for a population of users: normal behaviour with deliberate
hard negatives, plus scam journeys (7 workflows, some using an evasion). Each row is one
payment attempt with the features Satark's risk API would see at decision time, computed
point-in-time: only events strictly before that payment are used.

    python satark_sim.py                 # writes data/train.parquet, data/test.parquet, data/generator_card.md
    python satark_sim.py --users 500     # quick run

Two worlds with different seeds: "train" has many victims (oversampled positives), "test"
has a realistic scam rate. Nothing here is real data; every rate is listed in P with its basis.
"""
import argparse
import re
from collections import defaultdict, deque
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd

DAY = 86400.0

# Every knob and the basis for its value. generator_card.md is rendered from this dict.
P = {
    "days": (120, "simulated days per world"),
    "warmup_days": (30, "baselines build up first; scams start after this, earlier rows are flagged warmup"),
    "age_bands": ({"18-25": .25, "26-40": .35, "41-60": .25, "60+": .15}, "assumption: smartphone UPI user mix"),
    "languages": ({"hi": .45, "en": .30, "other": .25}, "assumption, used only for fairness slices"),
    "device_tiers": ({"low": .4, "mid": .4, "high": .2}, "assumption"),
    "assistive_share": (.02, "assumption: screen-reader users, slower typing and more pauses (hard negative)"),
    "remote_user_share": (.01, "assumption: users who keep a remote-access app for work (hard negative)"),
    "payments_per_day": ((0.8, 0.6), "per-user lognormal (median, sigma); assumption"),
    "balance_inr": ((25000, 1.0), "per-user lognormal (median, sigma); static, only used to size scam drains"),
    "legit_on_call": ((1.5, 15.0), "per-user Beta(a, b), mean about 9% of legit payments made on a call; A6 knob"),
    "legit_screen_share": (.003, "family helping with the app"),
    "legit_remote_new": (.001, "legit remote-access install in the last 24 h (IT help)"),
    "payee_mix": ({"merchant": .62, "friend": .30, "new_merchant": .06, "new_individual": .02}, "assumption"),
    "young_individual_share": (.15, "new legit individual payees whose account is under 60 days old"),
    "merchant_amount": ((180, 1.0), "lognormal INR (median, sigma)"),
    "friend_amount": ((600, 1.0), "lognormal INR (median, sigma)"),
    "rent_share": (.35, "users paying monthly rent by UPI"),
    "rent_amount": ((12000, .5), "lognormal INR"),
    "new_tenancy": (.10, "share of rent payers who move during the sim: deposit + rent to a new landlord"),
    "emergency_per_day": (1 / 600, "hospital or family emergency to a new payee, stressed, often on a call"),
    "emergency_amount": ((25000, .7), "lognormal INR"),
    "item_per_day": (1 / 250, "second-hand purchase from a new seller, often on a call"),
    "item_amount": ((6000, .8), "lognormal INR"),
    "device_change_per_day": (1 / 400, "legit new phone (hard negative for account takeover)"),
    "failed_pin": (.03, "legit PIN typo rate"),
    "legit_link_share": (.08, "merchant payments opened from a biller link (old, clean domains)"),
    "feed_false_positive": (.002, "clean link wrongly listed by a reputation feed"),
    "legit_qr_gallery": (.03, "legit payments to a QR image received in chat (tuition, small shops)"),
    "typing_ms": ((280, 60), "per-user mean ms per keystroke ~ Normal; +120 for 60+, +250 assistive"),
    "typing_cv": (.15, "session-to-session variation"),
    "pauses": ((.3, 1.0), "per-user Poisson mean range for pauses over 2 s; +1.5 assistive"),
    "pin_secs": (4.0, "median seconds on the PIN step; x1.4 for 60+, x1.6 assistive"),
    "n_merchants": (3000, "merchant pool shared by all users"),
    "new_shop_share": (.10, "merchants created during the sim"),
    "verified": ({"old": .75, "new": .30}, "verified merchant share"),
    "brandlike_share": (.03, "legit small shops with a brand word in the handle (hard negative)"),
    "merchant_new_payers": ((2.0, 1.2), "background first-time payers per day, lognormal (median, sigma)"),
    "mule_age_days": ({(1, 30): .5, (30, 365): .3, (365, 2000): .2},
                      "account age at first scam use; MuleHunter's typologies include dormant accounts suddenly active"),
    "mule_active_days": ((3, 15), "how long a mule account stays active"),
    "mule_new_payers": ((2, 25), "background victims per day while active (other users of the PSP)"),
    "aged_mule_new_payers": ((.3, 3), "bought, aged accounts stay low-volume"),
    "mule_reuse": (.5, "scam payment goes to an already-active mule"),
    "report_prob": (.4, "victim reports in-app after realising"),
    "report_delay_h": ((2, 72), "hours from last scam payment to report"),
    "bg_report_rate": (.05, "background mule payers who report"),
    "false_report_per_day": (1 / 3000, "legit payee falsely reported (misuse case)"),
    "victim_share": ({"train": .15, "test": .012}, "train is oversampled; test lands near 1 scam per 2,000 to 4,000 payments"),
    "evasive_share": (.2, "journeys that use one evasion"),
}


def p(k):
    return P[k][0]


# Scam workflows. ages: relative susceptibility; coached: behaviour shift (full, mild, ato);
# entry: channel mix; n: payments per journey; same_payee: chance the next step reuses the payee.
SCEN = {
    "digital_arrest": dict(share=.15, ages={"60+": 3, "41-60": 2}, n=(1, 3), coached="full", on_call=.92,
                           screen=.10, remote=.05, entry={"typed_vpa": 1}, lookalike=0, hours=(10, 19),
                           same_payee=.3, gap_h=(1, 30), notes=("legal", .5), drain=(.5, .95)),
    "customer_care": dict(share=.18, ages={}, n=(1, 2), coached="full", on_call=.9, screen=.7, remote=.6,
                          entry={"typed_vpa": .7, "qr_gallery": .3}, lookalike=.5, hours=(9, 21),
                          same_payee=.5, gap_h=(.1, 2), notes=("refund", .6), amount=(3000, .8)),
    "kyc_link": dict(share=.15, ages={"41-60": 1.5, "60+": 1.5}, n=(1, 2), coached="mild", on_call=.25,
                     screen=.05, remote=.1, entry={"deep_link_sms": 1}, lookalike=.7, hours=(8, 22),
                     same_payee=.8, gap_h=(.05, .5), notes=("kyc", .5), amount=(4000, .9)),
    "task_scam": dict(share=.17, ages={"18-25": 3, "26-40": 2}, n=(3, 6), coached="mild", on_call=.05, screen=0,
                      remote=0, entry={"typed_vpa": .5, "contact": .5}, lookalike=0, hours=(18, 24),
                      same_payee=.7, gap_h=(3, 48), notes=("task", .6), amount=(500, .5), escalate=(2, 4)),
    "investment": dict(share=.15, ages={"26-40": 2, "41-60": 2}, n=(2, 5), coached="mild", on_call=.15, screen=0,
                       remote=0, entry={"typed_vpa": .6, "deep_link_whatsapp": .4}, lookalike=0, hours=(9, 23),
                       same_payee=.4, gap_h=(24, 240), notes=("investment", .5), amount=(15000, .7),
                       escalate=(1.2, 2.5)),
    "fake_qr": dict(share=.12, ages={"18-25": 1.5, "26-40": 1.5}, n=(1, 2), coached="mild", on_call=.5, screen=0,
                    remote=0, entry={"qr_gallery": .9, "qr_scan": .1}, lookalike=0, hours=(9, 22),
                    same_payee=.9, gap_h=(.02, .3), notes=("receive", .4), amount=(5000, .8)),
    "otp_takeover": dict(share=.08, ages={}, n=(1, 3), coached="ato", on_call=0, screen=0, remote=.2,
                         entry={"typed_vpa": 1}, lookalike=0, hours=(0, 24), same_payee=.6, gap_h=(.02, .5),
                         notes=(None, 0), drain=(.5, .95)),
}
EVASIONS = ["hang_up_first", "aged_mule", "no_link", "calm_victim"]

FEATURES = {
    "A_session": ["on_call", "screen_shared", "remote_app_present", "remote_app_new", "app_switches",
                  "typing_z", "pause_z", "pin_time_z", "device_new", "failed_auth"],
    "B_payee": ["payee_first_time", "payee_age_days", "payee_verified", "payee_new_payers_24h",
                "payee_reports_prior", "lookalike_score"],
    "C_context": ["entry_channel", "link_bad", "link_domain_age_days", "secs_link_to_pay", "note_text"],
    "D_baseline": ["amount", "amount_ratio", "amount_z", "amount_vs_max", "hour", "hour_familiarity",
                   "same_payee_count_24h", "same_payee_sum_24h", "escalation_ratio", "baseline_ready"],
}
META = ["event_id", "ts", "day", "user_id", "payee_id", "is_scam", "scenario", "variant", "journey_id", "step",
        "hard_negative", "age_band", "language", "device_tier", "assistive_tech", "warmup", "note_intent", "world"]

NOTES = {
    "legal": ["verification amount", "case clearance", "rbi safe account", "as per officer", "cbi verification"],
    "refund": ["refund processing", "cashback approve", "refund ke liye", "order refund charge", "refund"],
    "kyc": ["kyc update fee", "account verify charge", "pan link fee", "kyc pending", "sim kyc"],
    "task": ["task deposit", "level upgrade", "prepaid task", "task 3 recharge", "commission unlock"],
    "investment": ["ipo allotment", "trading deposit", "vip group fee", "stock tips plan", "withdrawal tax"],
    "receive": ["receive payment", "olx payment", "token amount", "to receive money", "buyer payment"],
    "food": ["dinner", "lunch", "chai", "swiggy split", "party"],
    "home": ["rent", "milk", "maid salary", "electricity", "groceries"],
    "family": ["for mummy", "urgent pls send", "hospital bill", "fees", "emergency yaar"],
    "misc": ["thanks bhai", "ticket", "gift", "petrol", "refund for ticket", "advance", "token amount for flat"],
}
FIRST = ["rahul", "priya", "amit", "sneha", "vikram", "anjali", "arjun", "pooja", "rohit", "neha", "suresh",
         "kavita", "manoj", "deepa", "sanjay", "meena", "ravi", "asha", "karan", "divya", "imran", "fatima",
         "joseph", "mary", "gurpreet", "venkat", "lakshmi", "arun", "geeta", "nitin"]
SHOP = ["sharma", "gupta", "balaji", "sai", "krishna", "royal", "shree", "annapurna", "city", "om", "jai", "star"]
KIND = ["kirana", "medical", "electronics", "sweets", "mobile", "garments", "hardware", "dhaba", "chemist",
        "bakery", "salon", "traders"]
BRANDS = ["sbi", "hdfc", "icici", "axis", "paytm", "phonepe", "gpay", "amazon", "flipkart", "irctc", "airtel",
          "jio", "lic", "uidai", "incometax", "npci", "rbi", "myntra", "swiggy", "zomato"]
SCAM_WORDS = ["kyc", "care", "help", "refund", "support", "desk", "verify", "update", "cashback"]
PSP = ["@ybl", "@okaxis", "@oksbi", "@paytm", "@okhdfcbank", "@ibl", "@axl"]
CONFUSABLE = str.maketrans("01345", "oieas")
_look_cache = {}


def lookalike(handle, verified):
    """Similarity of the handle to a brand, after folding digit homoglyphs (0->o, 1->i ...).
    Verified merchants score 0: an official handle is not a look-alike."""
    if verified:
        return 0.0
    best = 0.0
    for tok in re.split(r"[^a-z0-9]+", handle.split("@")[0].lower()):
        if len(tok) < 3 or sum(c.isdigit() for c in tok) * 2 > len(tok):
            continue
        tok = tok.translate(CONFUSABLE)
        if tok not in _look_cache:
            _look_cache[tok] = max(SequenceMatcher(None, tok, b).ratio() for b in BRANDS)
        best = max(best, _look_cache[tok])
    return round(best, 3)


class World:
    def __init__(self, name, seed, n_users):
        self.name, self.n_users = name, n_users
        self.rng = np.random.default_rng(seed)
        self.days = p("days")
        self.pk, self.pc, self.pv, self.ph, self.pl, self.pa, self.pu = [], [], [], [], [], [], []
        self.events, self.reports, self.mules = [], [], []
        self._bg, self._look = {}, {}

    # payees -------------------------------------------------------------------------------
    def add_payee(self, kind, created_ts, verified, handle, lam, active=None):
        self.pk.append(kind); self.pc.append(created_ts); self.pv.append(verified); self.ph.append(handle)
        self.pl.append(lam); self.pa.append(active); self.pu.append(self.rng.random())
        return len(self.pk) - 1

    def look(self, pe):
        if pe not in self._look:
            self._look[pe] = lookalike(self.ph[pe], self.pv[pe])
        return self._look[pe]

    def person_handle(self):
        r = self.rng
        return f"{r.choice(FIRST)}.{r.integers(10, 9999)}{r.choice(PSP)}"

    def shop_handle(self):
        r = self.rng
        return f"{r.choice(SHOP)}-{r.choice(KIND)}-{r.integers(1, 99)}{r.choice(PSP)}"

    def scam_handle(self):
        r = self.rng
        b = list(r.choice(BRANDS))
        op = r.integers(4)
        i = r.integers(len(b))
        if op == 0:
            b = ["0" if c == "o" else "1" if c in "il" else c for c in b]
        elif op == 1:
            b.insert(i, b[i])
        elif op == 2 and len(b) > 3:
            b.pop(i)
        elif op == 3 and i < len(b) - 1:
            b[i], b[i + 1] = b[i + 1], b[i]
        return f"{''.join(b)}{r.choice(['-', '.', ''])}{r.choice(SCAM_WORDS)}{r.choice(PSP)}"

    def individual(self, young_share=0.0, ts=0.0):
        age = self.rng.uniform(5, 60) if self.rng.random() < young_share else self.rng.uniform(300, 3000)
        return self.add_payee("individual", ts - age * DAY, False, self.person_handle(), .03)

    def make_merchants(self):
        r = self.rng
        for b in BRANDS:
            self.add_payee("brand", -3000 * DAY, True, f"{b}{r.choice(PSP)}", 50.0)
        for _ in range(p("n_merchants")):
            new = r.random() < p("new_shop_share")
            created = r.uniform(0, self.days) * DAY if new else -r.lognormal(np.log(700), .8) * DAY
            ver = r.random() < p("verified")["new" if new else "old"]
            if r.random() < p("brandlike_share"):
                handle = f"{r.choice(BRANDS)}-{r.choice(KIND)}-point{r.choice(PSP)}"
            else:
                handle = self.shop_handle()
            lam = r.uniform(1, 15) if new else r.lognormal(np.log(p("merchant_new_payers")[0]), p("merchant_new_payers")[1])
            self.add_payee("new_shop" if new else "merchant", created, ver, handle, lam)
        self.merchants = np.arange(len(self.pk))
        self.m_created = np.array([self.pc[m] for m in self.merchants])
        w = np.array([self.pl[m] for m in self.merchants])
        self.m_weight = w / w.sum()

    def get_mule(self, ts, lookalike_handle, aged):
        r = self.rng
        if not aged and r.random() < p("mule_reuse"):
            live = [m for m in self.mules if self.pc[m] <= ts and self.pa[m][0] * DAY <= ts <= sum(self.pa[m]) * DAY
                    and (self.look(m) >= .75) == lookalike_handle]
            if live:
                return live[r.integers(len(live))]
        if aged:
            created, lam = ts - r.uniform(180, 900) * DAY, r.uniform(*p("aged_mule_new_payers"))
        else:
            ages, w = zip(*p("mule_age_days").items())
            created = ts - r.uniform(*ages[r.choice(len(ages), p=w)]) * DAY
            lam = r.uniform(*p("mule_new_payers"))
        handle = self.scam_handle() if lookalike_handle else (self.person_handle() if r.random() < .7 else self.shop_handle())
        m = self.add_payee("mule", created, False, handle, lam, (ts / DAY - r.uniform(0, 2), r.uniform(*p("mule_active_days"))))
        self.mules.append(m)
        return m

    def bg_new_payers(self, pe, day):
        """First-time payers from the rest of the platform on this day. ponytail: one Poisson draw
        per payee-day stands in for a rolling 24 h window."""
        key = (pe, day)
        if key not in self._bg:
            k, lam = self.pk[pe], self.pl[pe]
            if day * DAY < self.pc[pe] and k != "mule":
                rate = 0.0
            elif k == "new_shop":
                rate = lam * min(1.0, (day - self.pc[pe] / DAY + 1) / 10)
            elif k == "mule":
                a0, al = self.pa[pe]
                rate = lam if a0 <= day <= a0 + al else .05
            else:
                rate = lam
            self._bg[key] = int(self.rng.poisson(rate))
        return self._bg[key]

    def bg_reports(self, pe, day):
        """Reports filed before this day by users outside the simulated population. Monotone in day."""
        if self.pk[pe] == "mule":
            a0, al = self.pa[pe]
            exposure = max(0.0, min(day - 1, a0 + al) - a0) * self.pl[pe] * p("bg_report_rate")
        else:
            exposure = max(0.0, day - max(0.0, self.pc[pe] / DAY)) * p("false_report_per_day") * (1 + self.pl[pe] / 10)
        return int(exposure + self.pu[pe])

    # users and legit behaviour ---------------------------------------------------------------
    def make_users(self):
        r, users = self.rng, []
        bands, bw = zip(*p("age_bands").items())
        langs, lw = zip(*p("languages").items())
        tiers, tw = zip(*p("device_tiers").items())
        old = self.merchants[self.m_created <= 0]
        ow = self.m_weight[self.m_created <= 0] / self.m_weight[self.m_created <= 0].sum()
        for uid in range(self.n_users):
            age = r.choice(bands, p=bw)
            assist = r.random() < p("assistive_share")
            mu = r.normal(*p("typing_ms")) + (120 if age == "60+" else 0) + (250 if assist else 0)
            u = dict(id=uid, age=age, lang=r.choice(langs, p=lw), tier=r.choice(tiers, p=tw), assist=assist,
                     remote=r.random() < p("remote_user_share"),
                     rate=r.lognormal(np.log(p("payments_per_day")[0]), p("payments_per_day")[1]),
                     balance=r.lognormal(np.log(p("balance_inr")[0]), p("balance_inr")[1]),
                     on_call=r.beta(*p("legit_on_call")), typing=max(120.0, mu),
                     pause=r.uniform(*p("pauses")) + (1.5 if assist else 0),
                     pin=p("pin_secs") * (1.4 if age == "60+" else 1) * (1.6 if assist else 1),
                     peaks=[(r.uniform(7, 23), r.uniform(.5, 2.5)) for _ in range(r.integers(1, 4))],
                     friends=[self.individual() for _ in range(r.integers(8, 26))],
                     favs=list(r.choice(old, size=r.integers(10, 31), replace=False, p=ow)),
                     rent=None, device_new=False)
            if r.random() < p("rent_share"):
                u["rent"] = (self.individual(), r.integers(1, 28),
                             r.lognormal(np.log(p("rent_amount")[0]), p("rent_amount")[1]),
                             r.integers(p("warmup_days"), self.days) if r.random() < p("new_tenancy") else None)
            users.append(u)
        self.users = users

    def hour(self, u):
        mu, sd = u["peaks"][self.rng.integers(len(u["peaks"]))]
        return float(self.rng.normal(mu, sd) % 24)  # wrap past midnight; clipping piled payments onto one timestamp

    def session(self, u, mode):
        r = self.rng
        t = u["typing"] * (1 + p("typing_cv") * r.standard_normal())
        pauses = int(r.poisson(u["pause"]))
        pin = u["pin"] * float(np.exp(.3 * r.standard_normal()))
        sw = int(r.poisson(.4))
        if mode == "on_call":
            sw = int(r.poisson(1.2))
        elif mode == "stressed":
            t *= 1.1; pauses += int(r.poisson(1)); sw = int(r.poisson(1.2))
        elif mode == "full":
            t *= r.uniform(1.15, 1.6); pauses += int(r.integers(1, 5)); pin *= r.uniform(1.3, 2.5); sw = int(r.poisson(2.5))
        elif mode == "mild":
            t *= r.uniform(1.0, 1.25); pauses += int(r.integers(0, 3)); pin *= r.uniform(1.0, 1.6); sw = int(r.poisson(1.8))
        elif mode == "ato":
            t *= .6; pauses = 0; pin *= .3; sw = 0
        return dict(typing_ms=max(60.0, t), pauses=pauses, pin_secs=max(.5, pin), app_switches=sw)

    def note(self, intent, p_text):
        r = self.rng
        if intent is None or r.random() > p_text:
            return "", "none"
        t = str(r.choice(NOTES[intent]))
        if r.random() < .3:
            t += " " + str(r.choice(["bhai", "ji", "pls", "sir", "asap"]))
        if r.random() < .1 and len(t) > 4:
            i = int(r.integers(len(t)))
            t = t[:i] + t[i + 1:]
        return (t.upper() if r.random() < .1 else t), intent

    def emit(self, u, ts, payee, amount, mode="legit", entry="contact", intent=None, p_text=.4, on_call=None,
             screen=False, remote_new=False, link=None, tags=(), scam=None, failed=None):
        r = self.rng
        if on_call is None:
            on_call = r.random() < u["on_call"]
        if not scam and on_call:
            tags = (*tags, "on_call_legit")
        if mode == "legit" and on_call:
            mode = "on_call"
        if not scam and r.random() < p("legit_screen_share"):
            screen, tags = True, (*tags, "family_screen_share")
        if not scam and r.random() < p("legit_remote_new"):
            remote_new, tags = True, (*tags, "legit_remote_install")
        if u["remote"]:
            tags = (*tags, "remote_app_user")
        if u["assist"]:
            tags = (*tags, "assistive_user")
        device_new = u["device_new"] or (scam is not None and scam["scenario"] == "otp_takeover")
        if u["device_new"]:
            u["device_new"] = False
            if not scam:
                tags = (*tags, "device_change")
        if failed is None:
            failed = int(r.random() < p("failed_pin"))
        text, nint = self.note(intent, p_text)
        s = self.session(u, mode)
        ev = dict(ts=ts, user_id=u["id"], payee_id=payee, amount=round(float(amount), 2), entry_channel=entry,
                  on_call=int(on_call), screen_shared=int(screen), remote_app_present=int(remote_new or u["remote"]),
                  remote_app_new=int(remote_new), device_new=int(device_new), failed_auth=failed,
                  link_bad=np.nan, link_domain_age_days=np.nan, secs_link_to_pay=np.nan,
                  note_text=text, note_intent=nint, hard_negative="|".join(dict.fromkeys(tags)),
                  is_scam=0, scenario="legit", variant="", journey_id=-1, step=-1, **s)
        if link:
            ev.update(link_bad=int(link[0]), link_domain_age_days=link[1], secs_link_to_pay=link[2])
        if scam:
            ev.update(is_scam=1, **scam)
        self.events.append(ev)

    def legit_activity(self):
        r = self.rng
        mix_k, mix_w = zip(*p("payee_mix").items())
        for u in self.users:
            counts = r.poisson(u["rate"], self.days)
            for d in range(self.days):
                if r.random() < p("device_change_per_day"):
                    u["device_new"] = True
                for _ in range(counts[d]):
                    ts = d * DAY + self.hour(u) * 3600
                    k = r.choice(mix_k, p=mix_w)
                    if k == "friend" or k == "new_individual":
                        if k == "new_individual":
                            u["friends"].append(self.individual(p("young_individual_share"), ts))
                            pe, tags = u["friends"][-1], ("new_individual",)
                        else:
                            pe, tags = u["friends"][min(int(r.zipf(1.6)) - 1, len(u["friends"]) - 1)], ()
                        amt = r.lognormal(np.log(p("friend_amount")[0]), p("friend_amount")[1])
                        intent = r.choice(["food", "misc", "family", "home"], p=[.4, .35, .15, .1])
                        entry = r.choice(["contact", "qr_scan", "typed_vpa", "qr_gallery"], p=[.75, .1, .12, .03])
                        self.emit(u, ts, pe, min(amt, .9 * u["balance"]), entry=entry, intent=intent, tags=tags)
                        continue
                    if k == "new_merchant":
                        ok = self.m_created <= ts
                        w = self.m_weight * ok
                        pe = int(r.choice(self.merchants, p=w / w.sum()))
                        if pe not in u["favs"]:
                            u["favs"].append(pe)
                        tags = ("new_shop",) if self.pk[pe] == "new_shop" else ()
                    else:
                        pe = u["favs"][min(int(r.zipf(1.4)) - 1, len(u["favs"]) - 1)]
                        tags = ()
                    if self.look(pe) >= .8:
                        tags = (*tags, "brandlike_shop")
                    amt = r.lognormal(np.log(p("merchant_amount")[0]), p("merchant_amount")[1])
                    link, entry = None, r.choice(["qr_scan", "typed_vpa", "merchant_collect"], p=[.8, .1, .1])
                    if r.random() < p("legit_link_share"):
                        entry = r.choice(["deep_link_sms", "deep_link_whatsapp"])
                        link = (r.random() < p("feed_false_positive"), r.lognormal(np.log(2000), .8), r.uniform(20, 600))
                        tags = (*tags, "legit_link")
                    elif r.random() < p("legit_qr_gallery"):
                        entry, tags = "qr_gallery", (*tags, "qr_gallery_legit")
                    self.emit(u, ts, pe, min(amt, .9 * u["balance"]), entry=entry, intent="home", p_text=.15,
                              link=link, tags=tags)
            self.scheduled(u)

    def scheduled(self, u):
        """Rent, tenancy moves, emergencies and second-hand purchases: the large first-time legit payments."""
        r = self.rng
        if u["rent"]:
            landlord, dom, amt, move = u["rent"]
            for d in range(dom, self.days, 30):
                tags = ()
                if move is not None and d >= move:
                    if landlord == u["rent"][0]:
                        landlord = self.individual(.2, d * DAY)
                        self.emit(u, d * DAY + self.hour(u) * 3600 - 7200, landlord, min(2.5 * amt, .9 * u["balance"]),
                                  entry="typed_vpa", intent="misc", p_text=.6, tags=("new_tenancy_deposit",))
                        tags = ("new_tenancy_rent",)
                self.emit(u, d * DAY + self.hour(u) * 3600, landlord, min(amt, .9 * u["balance"]), entry="contact",
                          intent="home", p_text=.7, tags=tags)
        for d in range(self.days):
            if r.random() < p("emergency_per_day"):
                ts = d * DAY + r.uniform(0, 24) * 3600
                pe = self.individual(p("young_individual_share"), ts)
                amt = r.lognormal(np.log(p("emergency_amount")[0]), p("emergency_amount")[1])
                self.emit(u, ts, pe, min(amt, .9 * u["balance"]), mode="stressed", entry="typed_vpa", intent="family",
                          p_text=.6, on_call=r.random() < .5, tags=("emergency",))
            if r.random() < p("item_per_day"):
                ts = d * DAY + self.hour(u) * 3600
                pe = self.individual(.3, ts)
                amt = r.lognormal(np.log(p("item_amount")[0]), p("item_amount")[1])
                self.emit(u, ts, pe, min(amt, .9 * u["balance"]), entry=r.choice(["qr_gallery", "typed_vpa"]),
                          intent="misc", p_text=.5, on_call=r.random() < .4, tags=("item_purchase",))

    # scams ------------------------------------------------------------------------------------
    def scams(self):
        r = self.rng
        names = list(SCEN)
        shares = np.array([SCEN[s]["share"] for s in names])
        n_victims = int(round(p("victim_share")[self.name] * self.n_users))
        taken = set()
        for jid in range(n_victims):
            scen = names[r.choice(len(names), p=shares / shares.sum())]
            s = SCEN[scen]
            w = np.array([0.0 if u["id"] in taken else s["ages"].get(u["age"], 1.0) for u in self.users])
            u = self.users[int(r.choice(len(w), p=w / w.sum()))]
            taken.add(u["id"])
            options = [e for e in EVASIONS if (e != "hang_up_first" or s["on_call"] > .3)
                       and (e != "no_link" or scen == "kyc_link") and (e != "calm_victim" or s["coached"] != "ato")]
            variant = str(r.choice(options)) if r.random() < p("evasive_share") else ""
            self.journey(u, scen, jid, variant)

    def journey(self, u, scen, jid, variant):
        r, s = self.rng, SCEN[scen]
        day = r.uniform(p("warmup_days"), self.days - 3)
        lo, hi = s["hours"]
        hour = r.uniform(0, 5) if scen == "otp_takeover" and r.random() < .5 else r.uniform(lo, hi)
        ts = int(day) * DAY + min(hour, 23.99) * 3600
        n = int(r.integers(s["n"][0], s["n"][1] + 1))
        drain = r.uniform(*s["drain"]) * u["balance"] / n if "drain" in s else None
        payee, amt, used = None, None, []
        lookalike_handle = r.random() < s["lookalike"]
        for step in range(n):
            if payee is None or r.random() > s["same_payee"]:
                payee = self.get_mule(ts, lookalike_handle, variant == "aged_mule")
                used.append(payee)
            if drain:
                amt = drain * r.uniform(.7, 1.3)
            elif "escalate" in s and amt is not None:
                amt *= r.uniform(*s["escalate"])
            elif scen == "kyc_link" and step == 0 and r.random() < .4:
                amt = r.uniform(1, 10)
            else:
                amt = r.lognormal(np.log(s["amount"][0]), s["amount"][1])
            amt = float(np.clip(amt, 1, .95 * u["balance"]))
            ek, ew = zip(*s["entry"].items())
            entry = str(r.choice(ek, p=np.array(ew) / sum(ew)))
            if variant == "no_link" and entry.startswith("deep_link"):
                entry = "typed_vpa"
            link = None
            if entry.startswith("deep_link"):
                bad = r.random() < .45
                link = (bad, r.uniform(0, 30) if bad else r.uniform(0, 10), r.uniform(20, 300))
            hide = variant == "hang_up_first"
            mode = "legit" if variant == "calm_victim" else s["coached"]
            remote_new = r.random() < s["remote"]
            self.emit(u, ts, payee, amt, mode=mode, entry=entry, intent=s["notes"][0], p_text=s["notes"][1],
                      on_call=(r.random() < s["on_call"]) and not hide, screen=(r.random() < s["screen"]) and not hide,
                      remote_new=remote_new, link=link,
                      failed=int(r.integers(0, 4)) if scen == "otp_takeover" else None,
                      scam=dict(scenario=scen, variant=variant, journey_id=jid, step=step))
            ts += r.uniform(*s["gap_h"]) * 3600
        if r.random() < p("report_prob"):
            rts = ts + r.uniform(*p("report_delay_h")) * 3600
            self.reports += [(rts, pe) for pe in used]

    # point-in-time features -------------------------------------------------------------------
    def featurize(self):
        ev = pd.DataFrame(self.events)
        ev = ev[ev.ts < self.days * DAY].sort_values(["ts", "user_id"], kind="stable").reset_index(drop=True)
        reports = sorted(self.reports)
        rp, own_reports = 0, defaultdict(int)
        ust, pst = {}, {}
        cohort = float(np.median(ev.amount))
        out = defaultdict(list)
        for r in ev.itertuples(index=False):
            ts, uid, pe = r.ts, r.user_id, r.payee_id
            day, h = int(ts // DAY), int(ts // 3600 % 24)
            while rp < len(reports) and reports[rp][0] < ts:
                own_reports[reports[rp][1]] += 1
                rp += 1
            s = ust.get(uid)
            if s is None:
                s = ust[uid] = dict(amt=deque(), hb=[0] * 24, sess=deque(maxlen=50), pp={}, last={})
            while s["amt"] and s["amt"][0][0] < ts - 90 * DAY:
                _, _, oh = s["amt"].popleft()
                s["hb"][oh] -= 1
            past = [a for _, a, _ in s["amt"]]
            ready = len(past) >= 5
            med = median(past) if ready else cohort
            out["amount_ratio"].append(r.amount / med)
            if ready:
                logs = np.log(past)
                lm = float(np.median(logs))
                out["amount_z"].append((np.log(r.amount) - lm) / max(1.4826 * float(np.median(np.abs(logs - lm))), .25))
                out["amount_vs_max"].append(r.amount / max(past))
                out["hour_familiarity"].append((s["hb"][h - 1] + s["hb"][h] + s["hb"][(h + 1) % 24]) / len(past))
            else:
                out["amount_z"].append(0.0); out["amount_vs_max"].append(1.0); out["hour_familiarity"].append(.125)
            out["baseline_ready"].append(int(ready))
            sess = list(s["sess"])
            for name, idx, floor in (("typing_z", 0, .05), ("pause_z", 1, None), ("pin_time_z", 2, .1)):
                if len(sess) >= 5:
                    xs = [x[idx] for x in sess]
                    m = median(xs)
                    scale = max(1.4826 * median([abs(x - m) for x in xs]), floor * m if floor else .5)
                    out[name].append((getattr(r, ("typing_ms", "pauses", "pin_secs")[idx]) - m) / scale)
                else:
                    out[name].append(0.0)
            dq = s["pp"].get(pe)
            if dq is not None:
                while dq and dq[0][0] < ts - DAY:
                    dq.popleft()
            out["payee_first_time"].append(int(pe not in s["last"]))
            out["same_payee_count_24h"].append(len(dq) if dq else 0)
            out["same_payee_sum_24h"].append(sum(a for _, a in dq) if dq else 0.0)
            out["escalation_ratio"].append(r.amount / s["last"][pe] if pe in s["last"] else 1.0)
            ps = pst.get(pe)
            if ps is None:
                ps = pst[pe] = (set(), deque())
            while ps[1] and ps[1][0][0] < ts - DAY:
                ps[1].popleft()
            is_new_payer = uid not in ps[0]
            out["payee_new_payers_24h"].append(sum(f for _, f in ps[1]) + self.bg_new_payers(pe, day))
            out["payee_reports_prior"].append(own_reports[pe] + self.bg_reports(pe, day))
            out["payee_age_days"].append((ts - self.pc[pe]) / DAY)
            out["payee_verified"].append(int(self.pv[pe]))
            out["lookalike_score"].append(self.look(pe))
            out["hour"].append(h)
            # update state only after features are computed (point-in-time)
            s["amt"].append((ts, r.amount, h)); s["hb"][h] += 1
            s["sess"].append((r.typing_ms, r.pauses, r.pin_secs))
            s["pp"].setdefault(pe, deque()).append((ts, r.amount)); s["last"][pe] = r.amount
            ps[0].add(uid); ps[1].append((ts, int(is_new_payer)))
        df = pd.concat([ev, pd.DataFrame(out)], axis=1)
        users = pd.DataFrame([dict(user_id=u["id"], age_band=u["age"], language=u["lang"], device_tier=u["tier"],
                                   assistive_tech=int(u["assist"])) for u in self.users])
        df = df.merge(users, on="user_id", how="left")
        df["event_id"] = np.arange(len(df))
        df["day"] = (df.ts // DAY).astype(int)
        df["warmup"] = (df.day < p("warmup_days")).astype(int)
        df["world"] = self.name
        cols = META + [c for fam in FEATURES.values() for c in fam if c not in META]
        return df[cols + ["typing_ms", "pauses", "pin_secs"]]


def generate(name, seed, n_users):
    w = World(name, seed, n_users)
    w.make_merchants()
    w.make_users()
    w.legit_activity()
    w.scams()
    return w.featurize()


def write_card(path, stats):
    lines = ["# Satark simulator generator card", "",
             "Rendered by `satark_sim.py` from its parameter table. Every value is an assumption unless the basis says",
             "otherwise; plan assumption A6 asks you to re-tune thresholds with key rates at half and double.", "",
             "## Parameters", "", "| Parameter | Value | Basis |", "|---|---|---|"]
    lines += [f"| `{k}` | {v} | {why} |" for k, (v, why) in P.items()]
    lines += ["", "## Scam workflows", "", "| Scenario | Share | Payments | Coached | On call | Screen share | Entry |",
              "|---|---|---|---|---|---|---|"]
    lines += [f"| {k} | {s['share']} | {s['n'][0]}-{s['n'][1]} | {s['coached']} | {s['on_call']} | {s['screen']} | "
              f"{', '.join(s['entry'])} |" for k, s in SCEN.items()]
    lines += ["", f"Evasions (one per evasive journey): {', '.join(EVASIONS)}.", "", "## Columns", ""]
    lines += [f"- **{fam}**: {', '.join(cols)}" for fam, cols in FEATURES.items()]
    lines += [f"- **meta (never a model input)**: {', '.join(META)}",
              "- **raw session values** (inputs to the z-scores): typing_ms, pauses, pin_secs", "", "## Worlds", ""]
    lines += [f"- **{k}**: {v}" for k, v in stats.items()]
    lines += ["", "## Known limitations", "",
              "- Background platform activity (other users paying the same payee) is one Poisson draw per payee-day.",
              "- Balances are static and only size scam drains; the app does not see them.",
              "- Mule outbound flows and cash-out timing are not simulated.",
              "- Handles are generated from small word lists; real handle distributions differ.",
              "- Behaviour shifts under coaching follow published vendor descriptions, not measured Indian data."]
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--users", type=int, default=5000)
    ap.add_argument("--out", default=str(Path(__file__).parent / "data"))
    ap.add_argument("--seeds", type=int, nargs=2, default=(11, 22), help="train and test seeds")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name, seed in zip(("train", "test"), a.seeds):
        df = generate(name, seed, a.users)
        df.to_parquet(out / f"{name}.parquet", index=False)
        live = df[df.warmup == 0]
        stats[name] = (f"seed {seed}, {a.users} users, {len(df):,} payments ({len(live):,} after warm-up), "
                       f"{int(live.is_scam.sum())} scam payments = 1 in {len(live) / max(1, live.is_scam.sum()):,.0f}")
        print(name, stats[name])
    write_card(out / "generator_card.md", stats)


if __name__ == "__main__":
    main()
