# Satark: team guide for RAKSHAM Track 02

This guide is for the team building **Satark** for the RAKSHAM AI Cybersecurity Hackathon (IIT Delhi with Amazon). It explains the problem, the idea, what we already learned, and exactly how to produce the Round 1 submission: the 10-slide pitch deck and the 3-page architecture overview, combined into one PDF. It also covers the 48-hour finale build so the plan we submit is one we can actually deliver.
 Read it once end to end before you start. After that, use the table of contents to jump to your part.

> **Our one-sentence pitch:** Satark is a scam-interruption layer inside UPI apps that recognises when a payment is being coached by a scammer and responds with a proportionate, explained pause instead of a blind block.

---

## Contents

1. [Quick start](#1-quick-start)
2. [The hackathon in one page](#2-the-hackathon-in-one-page)
3. [What is in this folder](#3-what-is-in-this-folder)
4. [Words you need to know](#4-words-you-need-to-know)
5. [The problem: coached UPI payments](#5-the-problem-coached-upi-payments)
6. [What we learned from our first idea](#6-what-we-learned-from-our-first-idea)
7. [The solution: how Satark works](#7-the-solution-how-satark-works)
8. [Data and models](#8-data-and-models) (includes how to read every metric)
9. [Existing solutions and what we borrow](#9-existing-solutions-and-what-we-borrow)
10. [Round 1 work plan: who does what](#10-round-1-work-plan-who-does-what)
11. [The pitch deck, slide by slide](#11-the-pitch-deck-slide-by-slide)
12. [The architecture overview, page by page](#12-the-architecture-overview-page-by-page)
13. [The appendix](#13-the-appendix)
14. [Evidence to collect before submitting](#14-evidence-to-collect-before-submitting)
15. [Design and writing rules for the PDF](#15-design-and-writing-rules-for-the-pdf)
16. [Final checks before you submit](#16-final-checks-before-you-submit)
17. [The 48-hour finale plan](#17-the-48-hour-finale-plan)
18. [Team rules on data, safety and honesty](#18-team-rules-on-data-safety-and-honesty)
19. [FAQ: questions judges and the team ask](#19-faq-questions-judges-and-the-team-ask)
20. [Sources](#20-sources)

---

## 7. The solution: how Satark works

### Where it sits

Satark is an **SDK inside a UPI app** plus a **risk API at the PSP's backend**. When the user has entered a payee and amount, before the NPCI PIN screen, the app asks the risk API for a tier. Payments to known payees and small amounts pass silently.

### Four signal families

| Family | Question it answers | Example signals | Computed where |
|---|---|---|---|
| **A. Coercion in the session** | Is someone steering this person right now? | On a call (including WhatsApp calls), screen being shared, remote-access app enabled or newly installed, switching between chat and the payment screen, hesitation and pauses compared with the person's own baseline | Phone |
| **B. Payee risk** | Is the money going somewhere it should not? | First-time payee, payee account age, many new payers into the payee in 24 h, brand look-alike handle, verified merchant or not, in-app scam reports on the payee | Server |
| **C. Context** | What story is the user being told? | Intent of the payment note (refund, KYC, police, task, investment), urgency, entry channel (link from SMS or WhatsApp, QR from a gallery image), reputation and age of the link's domain | Phone and server |
| **D. Personal baseline** | Is this normal for this person? | Amount vs own history, escalating payments to the same new payee, unusual hour for this user | Server |

### Decision logic, in order

1. **Eligibility gate.** Only score payments that matter: first-time or recent payee, or amount well above the user's usual. Everything else passes silently. This removes most of the false-alarm surface.
2. **Family scores.** Each family gives a sub-score and its reasons.
3. **Fusion.** One gradient-boosted model over all features, plus a rules layer for payees an analyst has confirmed as scam accounts. SHAP values become plain-language reason codes.
4. **Corroboration rule.** A red pause needs **at least two families** above threshold. No single weak signal can pause money.
5. **Campaign detector** (the "emerging scams" part). Every hour, cluster amber and red cases by payee, payee registration pattern, note-text meaning and reason codes. A new cluster goes to an analyst, who can push a new warning template and payee flag to every app within hours. Meaning-based text embeddings catch AI-paraphrased scam messages that keyword lists miss.

### Tiers

| Tier | Trigger | What the user sees | Human involvement |
|---|---|---|---|
| Green | Not eligible, or low risk | Nothing; normal PIN screen | None |
| Amber | One family elevated | One specific warning naming the scam type and the actual reasons; one tap to continue. Max one amber per user per week unless red | None; logged for campaign detection |
| Red | Two or more families agree | Smart pause: a cancellable hold (for example 30 minutes), a short "is someone on the phone telling you what to do?" check, optional trusted-contact confirmation, one tap to report via cybercrime.gov.in or 1930 | Case and evidence pack go to an analyst queue, prioritised by amount times risk, reviewed within the hold window |
| Decline | Analyst-confirmed scam payee only | Payment declined, with the reason and an appeal path | Analyst decision, auditable; never model-only |

### Alert-fatigue controls

- Alert budget: under 0.1% of all payments reach amber or red; per-user amber cap.
- Trusted payees (paid 3+ times over 30+ days) and verified merchants skip scoring unless Family A fires.
- Warnings name the scam type and the real reasons. Templates rotate, because identical warnings stop being read.
- User messages come from fixed, reviewed templates. No free-form LLM text in front of a user.
- Track heed rate (user cancels) and override-then-reported rate (scam we missed).

---

## 17. The 48-hour finale plan

### API contract sketch

Request from the app:

```json
{
  "txn_ref": "t-000123",
  "user_ref": "u-hash-9f2c",
  "payee_vpa": "kyc-helpdesk-update@ybl",
  "amount": 48000,
  "entry_channel": "typed_vpa",
  "session": {
    "on_call": true,
    "screen_shared": false,
    "remote_app_present": false,
    "remote_app_new": false,
    "app_switches": 3,
    "typing_ms": 410,
    "pauses": 4,
    "pin_secs": 9.2,
    "device_new": false
  },
  "context": { "note_intent": "legal", "link_domain": null, "secs_link_to_pay": null }
}
```

Response from the risk API:

```json
{
  "tier": "red",
  "reasons": ["ON_CALL", "NEW_PAYEE_YOUNG_ACCOUNT", "AMOUNT_8X_USUAL"],
  "template_id": "red_call_new_payee_v1",
  "hold_minutes": 30,
  "case_id": "c-7781"
}
```

The app never receives the score or the model weights, only the tier, reason codes and a template ID.

### Demo script (three journeys)

1. **Silent pass.** Pay a saved friend ₹450. Nothing appears. Point: legit users feel nothing.
2. **Red pause.** A teammate calls the phone as a "KYC officer". Pay ₹48,000 to a new look-alike handle. The red screen shows three reasons; hang up and cancel.
3. **Mule caught.** Fifteen simulated payers send to the same new payee within 10 minutes. The console shows the cluster; the analyst confirms; the next payer gets red with "reported by other users".

