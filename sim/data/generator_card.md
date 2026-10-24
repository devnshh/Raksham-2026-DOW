# Satark simulator generator card

Rendered by `satark_sim.py` from its parameter table. Every value is an assumption unless the basis says
otherwise; plan assumption A6 asks you to re-tune thresholds with key rates at half and double.

## Parameters

| Parameter | Value | Basis |
|---|---|---|
| `days` | 120 | simulated days per world |
| `warmup_days` | 30 | baselines build up first; scams start after this, earlier rows are flagged warmup |
| `age_bands` | {'18-25': 0.25, '26-40': 0.35, '41-60': 0.25, '60+': 0.15} | assumption: smartphone UPI user mix |
| `languages` | {'hi': 0.45, 'en': 0.3, 'other': 0.25} | assumption, used only for fairness slices |
| `device_tiers` | {'low': 0.4, 'mid': 0.4, 'high': 0.2} | assumption |
| `assistive_share` | 0.02 | assumption: screen-reader users, slower typing and more pauses (hard negative) |
| `remote_user_share` | 0.01 | assumption: users who keep a remote-access app for work (hard negative) |
| `payments_per_day` | (0.8, 0.6) | per-user lognormal (median, sigma); assumption |
| `balance_inr` | (25000, 1.0) | per-user lognormal (median, sigma); static, only used to size scam drains |
| `legit_on_call` | (1.5, 15.0) | per-user Beta(a, b), mean about 9% of legit payments made on a call; A6 knob |
| `legit_screen_share` | 0.003 | family helping with the app |
| `legit_remote_new` | 0.001 | legit remote-access install in the last 24 h (IT help) |
| `payee_mix` | {'merchant': 0.62, 'friend': 0.3, 'new_merchant': 0.06, 'new_individual': 0.02} | assumption |
| `young_individual_share` | 0.15 | new legit individual payees whose account is under 60 days old |
| `merchant_amount` | (180, 1.0) | lognormal INR (median, sigma) |
| `friend_amount` | (600, 1.0) | lognormal INR (median, sigma) |
| `rent_share` | 0.35 | users paying monthly rent by UPI |
| `rent_amount` | (12000, 0.5) | lognormal INR |
| `new_tenancy` | 0.1 | share of rent payers who move during the sim: deposit + rent to a new landlord |
| `emergency_per_day` | 0.0016666666666666668 | hospital or family emergency to a new payee, stressed, often on a call |
| `emergency_amount` | (25000, 0.7) | lognormal INR |
| `item_per_day` | 0.004 | second-hand purchase from a new seller, often on a call |
| `item_amount` | (6000, 0.8) | lognormal INR |
| `device_change_per_day` | 0.0025 | legit new phone (hard negative for account takeover) |
| `failed_pin` | 0.03 | legit PIN typo rate |
| `legit_link_share` | 0.08 | merchant payments opened from a biller link (old, clean domains) |
| `feed_false_positive` | 0.002 | clean link wrongly listed by a reputation feed |
| `legit_qr_gallery` | 0.03 | legit payments to a QR image received in chat (tuition, small shops) |
| `typing_ms` | (280, 60) | per-user mean ms per keystroke ~ Normal; +120 for 60+, +250 assistive |
| `typing_cv` | 0.15 | session-to-session variation |
| `pauses` | (0.3, 1.0) | per-user Poisson mean range for pauses over 2 s; +1.5 assistive |
| `pin_secs` | 4.0 | median seconds on the PIN step; x1.4 for 60+, x1.6 assistive |
| `n_merchants` | 3000 | merchant pool shared by all users |
| `new_shop_share` | 0.1 | merchants created during the sim |
| `verified` | {'old': 0.75, 'new': 0.3} | verified merchant share |
| `brandlike_share` | 0.03 | legit small shops with a brand word in the handle (hard negative) |
| `merchant_new_payers` | (2.0, 1.2) | background first-time payers per day, lognormal (median, sigma) |
| `mule_age_days` | {(1, 30): 0.5, (30, 365): 0.3, (365, 2000): 0.2} | account age at first scam use; MuleHunter's typologies include dormant accounts suddenly active |
| `mule_active_days` | (3, 15) | how long a mule account stays active |
| `mule_new_payers` | (2, 25) | background victims per day while active (other users of the PSP) |
| `aged_mule_new_payers` | (0.3, 3) | bought, aged accounts stay low-volume |
| `mule_reuse` | 0.5 | scam payment goes to an already-active mule |
| `report_prob` | 0.4 | victim reports in-app after realising |
| `report_delay_h` | (2, 72) | hours from last scam payment to report |
| `bg_report_rate` | 0.05 | background mule payers who report |
| `false_report_per_day` | 0.0003333333333333333 | legit payee falsely reported (misuse case) |
| `victim_share` | {'train': 0.15, 'test': 0.012} | train is oversampled; test lands near 1 scam per 2,000 to 4,000 payments |
| `evasive_share` | 0.2 | journeys that use one evasion |

## Scam workflows

| Scenario | Share | Payments | Coached | On call | Screen share | Entry |
|---|---|---|---|---|---|---|
| digital_arrest | 0.15 | 1-3 | full | 0.92 | 0.1 | typed_vpa |
| customer_care | 0.18 | 1-2 | full | 0.9 | 0.7 | typed_vpa, qr_gallery |
| kyc_link | 0.15 | 1-2 | mild | 0.25 | 0.05 | deep_link_sms |
| task_scam | 0.17 | 3-6 | mild | 0.05 | 0 | typed_vpa, contact |
| investment | 0.15 | 2-5 | mild | 0.15 | 0 | typed_vpa, deep_link_whatsapp |
| fake_qr | 0.12 | 1-2 | mild | 0.5 | 0 | qr_gallery, qr_scan |
| otp_takeover | 0.08 | 1-3 | ato | 0 | 0 | typed_vpa |

Evasions (one per evasive journey): hang_up_first, aged_mule, no_link, calm_victim.

## Columns

- **A_session**: on_call, screen_shared, remote_app_present, remote_app_new, app_switches, typing_z, pause_z, pin_time_z, device_new, failed_auth
- **B_payee**: payee_first_time, payee_age_days, payee_verified, payee_new_payers_24h, payee_reports_prior, lookalike_score
- **C_context**: entry_channel, link_bad, link_domain_age_days, secs_link_to_pay, note_text
- **D_baseline**: amount, amount_ratio, amount_z, amount_vs_max, hour, hour_familiarity, same_payee_count_24h, same_payee_sum_24h, escalation_ratio, baseline_ready
- **meta (never a model input)**: event_id, ts, day, user_id, payee_id, is_scam, scenario, variant, journey_id, step, hard_negative, age_band, language, device_tier, assistive_tech, warmup, note_intent, world
- **raw session values** (inputs to the z-scores): typing_ms, pauses, pin_secs

## Worlds

- **train**: seed 11, 5000 users, 585,040 payments (439,624 after warm-up), 1773 scam payments = 1 in 248
- **test**: seed 22, 5000 users, 597,260 payments (448,127 after warm-up), 143 scam payments = 1 in 3,134

## Known limitations

- Background platform activity (other users paying the same payee) is one Poisson draw per payee-day.
- Balances are static and only size scam drains; the app does not see them.
- Mule outbound flows and cash-out timing are not simulated.
- Handles are generated from small word lists; real handle distributions differ.
- Behaviour shifts under coaching follow published vendor descriptions, not measured Indian data.
