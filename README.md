# Satark: scam interruption for UPI payments (RAKSHAM Track 02)

Satark checks a UPI payment **before the PIN screen** and decides whether the user is being coached by a scammer. It combines four signal families: the session (on a call, screen shared, remote-access app, typing rhythm), the payee (new to the user, reports, many new payers, look-alike handle), the context (note intent, link or QR entry) and the user's own baseline (unusual amount or hour). The answer is a tier with plain-language reasons: green (nothing shown), amber (one-tap warning), red (cancellable 30-minute pause with a check question, trusted contact and 1930 reporting) or decline (only for analyst-confirmed scam accounts).

The full team guide (problem, design, pitch and finale plan) is in [README_SATARK.md](README_SATARK.md). Backend details and API examples are in [BACKEND.md](BACKEND.md).

## What is in this repository

| Path | What it is |
|---|---|
| `app/` | Android demo UPI app (Kotlin, Jetpack Compose). A mock payment app: it never touches real UPI or real money. |
| `risk-sdk/` | The Satark SDK the app embeds: collects session signals on the phone, calls the Risk API, maps reason codes to English and Hindi text. |
| `api/` | Risk API (FastAPI): feature store (SQLite), policy engine, cases, reports, analyst confirmation, hash-chained audit log. |
| `model_service/` | Model Service: the trained XGBoost fusion model and its thresholds (the only copy of the model). |
| `scripts/` | Start scripts (macOS/Linux and Windows), demo seeding and `reset_demo_db.py`. |

## Run the backend

```bash
python3 -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```bash
python scripts/reset_demo_db.py
```

```bash
scripts/start_all.sh
```

On Windows use `scripts\start_all.bat` instead of the last command. The start script prints the analyst API key; analyst endpoints (`/v1/cases`, `/v1/payees/...`, `/internal/...`) need it in an `X-API-Key` header. Interactive API docs are at `http://127.0.0.1:8000/docs`.

## Run the app

Open the project in Android Studio and run the `app` configuration.

- **Emulator:** works as is (the app calls `http://10.0.2.2:8000`).
- **Real phone over USB:** forward the port, then build with the phone-side address (or set it in the app's Satark Lab screen):

```bash
adb reverse tcp:8000 tcp:8000
```

```bash
./gradlew :app:installDebug -PsatarkApiUrl=http://127.0.0.1:8000
```

## Before every demo

1. `python scripts/reset_demo_db.py`: seeded mule activity expires after 24 hours, and earlier runs count towards the weekly warning cap.
2. Start the backend and check `curl http://127.0.0.1:8000/health`.
3. On a real phone, run `adb reverse tcp:8000 tcp:8000` again after reconnecting USB.
4. Seeded journeys that work end to end: friend `rahul.sharma@oksbi` ₹450 (green), `kyc-helpdesk-update@ybl` ₹48,000 on a call (red), `mule.fastcash@okaxis` ₹25,000 (red), `vikram.singh@oksbi` ₹25,000 (amber), `confirmed-scam-mule@ybl` (blocked). A brand-new handle typed live gets a warning, not a red pause: red needs corroborating evidence about the payee.

## Tests

```bash
PYTHONPATH=. python -m pytest api/tests -q
```

Android unit tests: `./gradlew test` from Android Studio's terminal.

## Honest limits

- The model and thresholds come from our own simulator, not real bank data. Numbers are simulation results, not real-world accuracy.
- Screen sharing is detected only as an extra display (casting or mirroring); `device_new` and failed PIN attempts are not measured in this demo.
- One demo user (`raksham@oksbi`) is hard-coded in the app.
