# Holdout evaluation log

Every scoring of the holdout world (simulator seed 22) is appended here by `ml/evaluate.py --holdout`, and the last row is the number we report. Never re-run to pick a better result.

Before this log: the simulator's own `validate_sim.py` realism checks scored the seed-22 world with a throwaway model to validate the generator, and the earlier model bundle's training history is not recorded in this repo. Run 1 is the first holdout run of a model built by `ml/train.py`.

Simulation results on an unseen synthetic world, not real-world accuracy. Warning = amber or red screen.

| Run | Date (UTC) | Commit | Model sha256 | Thresholds sha256 | Model only: warning P / R | Model + policy: warning P / R / per 1,000 | Model + policy: red P / R | Results |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-24 06:41 | 8ac337d136 | 0502ccf91630 | f5fa4fcb5910 | 29.4% / 95.1% | 0.7% / 90.2% / 42.14 | 95.3% / 71.3% | `ml/results/holdout_run1.json` |

## Run 1: named failure cases

Written after run 1 from `ml/results/holdout_run1.json`. Nothing in the model, features or policy was changed in response. Deployed version = model plus policy; a miss means no amber or red screen.

Holdout: 448,127 payments after warm-up, 143 scam payments in 60 journeys. Every journey got at least one warning (model only and model plus policy); 14 scam payments got none.

Missed scams:
- **Later payments of a task scam, silenced by the weekly cap** (9 of the 14 misses end in `amber_cap_downgraded_to_green`, 6 of them task scams). The first payment of the journey was warned; the next ones were single-family ambers and the one-weak-amber-per-7-days cap turned them green. Fix: do not silence an amber for a payee the user was already warned about; escalate it instead.
- **Scam with no call, an unreported payee and a normal amount** (plan expectation; 6 holdout payments, 2 warned). Calm-victim task scams to a new payee at 0.7 to 1.3 times the usual amount score below the amber cut-off: the only signals are a new payee and fan-in. Fix: stronger payee-side mule features (first-time payers converging on a young individual account), which needs network data the simulator only approximates.
- **Notes do not rescue them.** Of the 9 sampled missed payments, 5 had no note at all; the other 4 had notes the keyword rules did label (task, refund, kyc), and the label alone was not enough. Fix: none from notes; this points back to the cap and payee fixes above.

False alarms (18,756 legit payments warned, 42.1 per 1,000; the model alone warns on 1.0 per 1,000):
- **Legit payments made on a call: 75% of all false alarms; 34% of on-call legit payments are warned.** Being on a call puts family A over its threshold, and an unverified shop with 5 or more new payers in 24 h, a new payee or an unusual amount fires a second family; the policy's "two families means amber" rule then warns whatever the model score. Fix: require the model's amber cut-off (or a payee-risk family other than shop fan-in) for a two-family amber, chosen on the validation world.
- **Family member helping over screen share: 100% warned** (7% of false alarms). The strong-coercion rule warns on any screen share by design; accepted cost, since it is also the customer-care scam's main signal.
- **Rent to a new landlord paid while on a call: 14 of 14 warned** (plan expectation, confirmed). New payee, large amount and a call fire three families.
- **Second-hand purchase from a new seller while on a call: 52% warned.** Same pattern as rent; the warning is one tap, but it is a real cost.
- **Screen-reader users: not worse in this run.** False-alarm rate 4.07% against 4.19% overall with the policy; with the model alone 0.09% against 0.07% overall. The plan expected more warnings for them; with the policy the call-driven false alarms swamp the typing-pause effect.

Fairness (warning false-alarm rate, model plus policy): every age band, language, phone tier and screen-reader group is between 4.07% and 4.30%, within 1.03 times the overall rate.

Unseen scam types (model only, retrained without that scenario, warning cut-off from the validation world): digital arrest 1.00, customer care 0.65, KYC link 0.71, task scam 0.65, investment 0.91, fake QR 0.67, OTP takeover 1.00.
