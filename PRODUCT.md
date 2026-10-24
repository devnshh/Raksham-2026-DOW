# Product

<!-- impeccable:product-schema 1 -->

## Platform

android

## Users

- **Primary:** an everyday UPI payer in India at the moment of paying, often a less confident digital user or a senior (pitch persona: Sunita, 61, retired teacher in Lucknow) who may be on a call with a scammer who is coaching them. Reads Hindi and English.
- **Operator:** a PSP or bank fraud analyst who reviews red cases and confirms scam accounts (backend analyst API; no analyst screen in the app).
- **Evaluators:** RAKSHAM hackathon judges watching a live demo on an emulator or phone, often projected.

## Product Purpose

Raksham UPI is a demo UPI payment app (a stand-in for a real PSP or bank app) with the Satark SDK embedded. Satark checks each payment before the PIN screen and, when a payment looks coached by a scammer, interrupts it in proportion: nothing for normal payments, a one-tap warning (amber), a cancellable 30-minute pause with a check question, trusted-contact and 1930 reporting (red), or a block for analyst-confirmed scam accounts (decline). Success: legit payments feel untouched; a coached victim understands within seconds why they were stopped and takes the safe action.

## Positioning

Satark does not try to detect AI voices or deepfakes. It detects the footprint every coached scam leaves at the payment step (a live call or screen share, a risky new payee, behaviour unusual for this person) and responds with explained, proportionate friction instead of a blind block.

## Operating Context

- A mock payment app: it never touches real UPI or real money.
- Flows: home, pay by phone number, pay by UPI ID, scan QR, amount and note entry, NPCI-style PIN sheet, receipt; Satark amber warning, red smart pause (hold timer, check question, trusted contact, report scam), decline; Simulation Lab with scripted demo scenarios and the API address setting.
- Talks to the Satark Risk API (FastAPI) at 10.0.2.2:8000 on the emulator.

## Capabilities and Constraints

- Jetpack Compose + Material 3, minSdk 24, targetSdk 34; light and dark themes.
- Risk decisions and reason codes come from the server; the app maps codes to English and Hindi text (risk-sdk ReasonMapper).
- One hard-coded demo user (raksham@oksbi).
- Payment notes never leave the phone; only an intent label is sent.

## Brand Commitments

- **Look:** the user chose to stay close to Google Pay's current Material 3 visual language (reference screenshots: dark and light home with search pill, four tonal action tiles, pill shortcuts, round contact avatars, extended "Scan QR" FAB, three-tab navigation bar). Follow that structure and craft level.
- **Not copied:** no Google, Google Pay or GPay names, logos or marks in the UI; the app is "Raksham UPI" and the protection layer is "Satark".
- **Motion:** every transition and animation must be fluent and user-friendly.

## Evidence on Hand

- Seeded demo payees and scenarios (api/db/seed.py, scripts/seed_demo.py, app simulation/DemoScenario.kt).
- No real customer data, testimonials or metrics; never fabricate them in the UI.

## Product Principles

1. Normal payments must feel exactly like a normal payment app: no extra screens, no nagging.
2. When Satark interrupts, the reason is specific, true, and readable in under five seconds, in Hindi and English.
3. The safe action (cancel, hang up, ask family) is always the most prominent; continuing is possible only where the tier allows it.
4. Never accuse without evidence; a block appears only for analyst-confirmed accounts.

## Accessibility & Inclusion

Warning screens are designed for seniors and low-confidence users first: large text that respects the system font size, plain words, Hindi and English with equal weight, 48 dp touch targets, high contrast in both themes.
