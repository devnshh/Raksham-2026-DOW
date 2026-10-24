# Holdout evaluation log

Every scoring of the holdout world (simulator seed 22) is appended here by `ml/evaluate.py --holdout`, and the last row is the number we report. Never re-run to pick a better result.

Before this log: the simulator's own `validate_sim.py` realism checks scored the seed-22 world with a throwaway model to validate the generator, and the earlier model bundle's training history is not recorded in this repo. Run 1 is the first holdout run of a model built by `ml/train.py`.

Simulation results on an unseen synthetic world, not real-world accuracy. Warning = amber or red screen.

| Run | Date (UTC) | Commit | Model sha256 | Thresholds sha256 | Model only: warning P / R | Model + policy: warning P / R / per 1,000 | Model + policy: red P / R | Results |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-24 06:41 | 8ac337d136 | 0502ccf91630 | f5fa4fcb5910 | 29.4% / 95.1% | 0.7% / 90.2% / 42.14 | 95.3% / 71.3% | `ml/results/holdout_run1.json` |
| 2 | 2026-10-24 16:03 | e5ff5d8154 | cfd7d027a7a9 | 8131fb36a3e7 | 29.9% / 96.5% | 6.2% / 95.8% / 4.92 | 96.3% / 72.0% | `ml/results/holdout_run2.json` |

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

## Between run 1 and run 2: what changed and why

Written before run 2. Every choice below was made from validation worlds (seeds 33, 44, 55), never the holdout.

- **Where the problem was found.** Before run 1, the validation run (seed 33) already showed 41 warnings per 1,000 payments with the policy against 1.0 for the model alone. Run 1 showed the same on the holdout. A breakdown on seed 33 then showed that 125 of the 127 scam payments warned were warned by the model; the "two families means amber" rule warned on about 15,900 genuine payments and caught 1 scam the model missed.
- **New signal: is the caller a saved contact.** Added to the simulator as `caller_in_contacts`, with assumed rates in the generator card (85% of legit on-call payments, fewer for new landlords, sellers and hospitals, 5% for scam callers, 30% for long task and investment cons). Drawn from its own random stream: every existing column of every world is unchanged (checked by hash). On the phone it is measured for incoming calls, counting only contacts saved at least 7 days ago.
- **Policy.** Amber now needs the model's amber threshold or screen sharing / a new remote-access app; two families alone no longer warn. A call with a saved contact adds little to the session family. The weekly warning cap is removed: with the two-family rule gone it only hid model warnings on the later payments of multi-step scams. Red is unchanged (model's red threshold and two families).
- **Model.** Retrained on seed 11 with the same hyperparameters; thresholds set on seed 33 at the same alert budgets (amber 0.856, red 0.996).
- **Validation, model plus policy, warning level:** seed 33 recall 96.5%, 5.0 warnings per 1,000, precision 6.3% (was 88.2%, 41.3, 0.7%); seed 44 95.0%, 5.0, 6.1%; seed 55 93.5%, 5.1, 5.8%. These are optimistic: thresholds were set on seed 33.
- **What run 2 can and cannot show.** The new signal's effect rests on the assumed rates above; the robustness run varies them. Run 2 is reported whatever it shows.

## Run 2: named failure cases

Written after run 2 from `ml/results/holdout_run2.json`. Nothing in the model, features or policy was changed in response.

Holdout: 448,127 payments after warm-up, 143 scam payments in 60 journeys. Every journey got at least one warning. 6 scam payments got none (run 1: 14). Model plus policy: recall 95.8%, precision 6.2%, 4.9 warnings per 1,000 (run 1: 90.2%, 0.7%, 42.1).

Missed scams:
- **Calm, no-call scams to an unreported payee** (5 of 6 misses end in `green_below_threshold`): two investment payments, two calm-victim task scams and one KYC-link payment. No call, no reports, and for the task scams a normal amount; the model scores them below the amber cut-off. Fix: payee-side network signals (many first-time payers into a young individual account), which the simulator only approximates.
- **A follow-up task-scam payment to a payee the user has paid before** (1, `eligibility_gate_silent_pass`): not a first-time payee and under twice the usual amount, so it was never scored. Fix: score repeat payments to a payee that has been reported since the last payment.

False alarms (2,068 genuine payments warned, 0.46%):
- **Screen sharing or a new remote-access app: 85% of false alarms** (family screen share 1,314, IT-help remote installs 442; every such payment is warned). This rule warns without the model. Fix to consider on validation: require the model's amber cut-off or another family alongside it, weighed against customer-care scams, where it is the main signal.
- **Payments made on a call: 232 false alarms, 0.56% of on-call genuine payments** (run 1: 13,987, 34%). Rent to a new landlord during a call: 0 of 14 warned (run 1: 14 of 14).
- **Emergency payments to a new person: 15% warned** (116); second-hand purchases 5%. Large first payments to young accounts score high even when legitimate.
- **Screen-reader users: not worse.** False-alarm rate 0.47% against 0.46% overall.

Fairness (warning false-alarm rate, model plus policy): every age band, language, phone tier and screen-reader group is between 0.44% and 0.49%.

Unseen scam types (model only, retrained without that scenario, warning cut-off from the validation world): digital arrest 1.00, customer care 0.65, KYC link 0.71, task scam 0.65, investment 0.91, fake QR 0.60, OTP takeover 1.00.

## After run 2: what the caller signal adds (validation, seed 33)

Same model and policy, with `caller_in_contacts` blanked so every call looks like an unknown caller: 5.22 warnings per 1,000 instead of 5.02, recall 139 of 144 either way. Almost all of the improvement from run 1 to run 2 comes from the policy change (no two-family amber, no weekly cap); the caller check removes a further 0.2 warnings per 1,000 in this simulation. The robustness run (seed 101) agrees: halving or doubling the saved-contact shares moves warnings between 4.7 and 4.9 per 1,000.

## Between run 2 and run 3: what changed and why

Written before run 3. Chosen on validation worlds (seeds 33, 44, 55), never the holdout.

- **Where it came from.** A demo test, not the holdout: paying Rs 50,000 to an unknown typed number was green. The model scored it 0.80 against the 0.856 amber cut-off; in the simulator, large first payments to people are mostly genuine (emergencies, second-hand purchases, new-landlord deposits), and the model learned that.
- **Rule added:** amber for a first payment of at least Rs 25,000 to a payee who is neither a saved contact (entry channel `contact`) nor a verified merchant (`stranger_amount_floor` in `policy.yaml`). Floors compared on validation before choosing: 10x usual and Rs 10,000 added about 2 warnings per 1,000; 20x and Rs 20,000 about 0.7; Rs 25,000 at any ratio about 0.4 to 0.5.
- **Validation, model plus policy, warning level, before and after:** seed 33 recall 96.5% both, 5.02 to 5.49 warnings per 1,000, precision 6.3% to 5.8%; seed 44 recall 95.0% both, 5.03 to 5.40; seed 55 recall 93.5% to 94.2% (one more scam), 5.14 to 5.63.
- **Also fixed, no effect on this replay:** the app's "Pay anyone" flow sent entry channel `phone_number`, which the model never saw; it now sends `typed_vpa` or `contact`, and the server maps unknown channels to `typed_vpa`.
- Run 3 is reported whatever it shows.
