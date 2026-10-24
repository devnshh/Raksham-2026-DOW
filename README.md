# Satark: scam interruption for UPI payments (RAKSHAM Track 02)

Satark checks a UPI payment **before the PIN screen** and decides whether the user is being coached by a scammer. It combines four signal families: the session (on a call, screen shared, remote-access app, typing rhythm), the payee (new to the user, reports, many new payers, look-alike handle), the context (note intent, link or QR entry) and the user's own baseline (unusual amount or hour). The answer is a tier with plain-language reasons: green (nothing shown), amber (one-tap warning), red (cancellable 30-minute pause with a check question, trusted contact and 1930 reporting) or decline (only for analyst-confirmed scam accounts).

The full team guide (problem, design, pitch and finale plan) is in [README_SATARK.md](README_SATARK.md). Backend details and API examples are in [BACKEND.md](BACKEND.md).

## What is in this repository

| Path | What it is |
|---|---|
| `app/` | Android demo UPI app (Kotlin, Jetpack Compose, Material 3), styled like a stock UPI app, light theme only. A mock payment app: it never touches real UPI or real money. |
| `risk-sdk/` | The Satark SDK the app embeds: collects session signals on the phone, calls the Risk API, maps reason codes to English and Hindi text. |
| `api/` | Risk API (FastAPI): feature store (SQLite), policy engine, cases, reports, analyst confirmation, hash-chained audit log. |
| `model_service/` | Model Service: the trained XGBoost fusion model and its thresholds (the only copy of the model). |
| `scripts/` | Start scripts (macOS/Linux and Windows), demo seeding and `reset_demo_db.py`. |
| `licenses/` | Licence for the bundled Google Sans font (SIL Open Font License 1.1). |

## Run the backend

Python 3.11. scikit-learn is pinned to 1.8.0 because the saved model needs it.

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

The demo database (`api/satark.db`) is not in git. After cloning or pulling, run `reset_demo_db.py` before starting the server.

## Run the app

Open the project in Android Studio and run the `app` configuration.

- **Gradle JDK:** set it to 17 (Settings → Build, Execution, Deployment → Build Tools → Gradle → Gradle JDK). Android Studio's bundled Java 25 cannot run this Gradle version.
- **Emulator:** give it 4 CPU cores (Device Manager → Edit → Advanced). With 1 core the first safety check can take longer than the app waits, and it shows "Safety check unavailable". The app calls `http://10.0.2.2:8000`.
- **Real phone over USB:** forward the port, then build with the phone-side address (or set it in the Simulation Lab):

```bash
adb reverse tcp:8000 tcp:8000
```

```bash
./gradlew :app:installDebug -PsatarkApiUrl=http://127.0.0.1:8000
```

Checked on a POCO M7 Plus 5G (Android 16). Notes for real phones:

- **Xiaomi, Redmi and POCO:** turn on "Install via USB" in Developer options, or the install fails with `INSTALL_FAILED_USER_RESTRICTED`, and tap Install on the phone when it asks.
- **Check the tunnel** by opening `http://127.0.0.1:8000/health` in the phone's browser. If the browser loads it but the app shows "Safety check unavailable", run `adb logcat -s RiskGate` to see why the app could not connect.
- **Wi-Fi instead of USB** only works on a network that lets devices reach each other; office and venue Wi-Fi often blocks that. A phone hotspot with the laptop joined to it should work (not tested here); set the laptop's address in the Simulation Lab.
- **Live call:** answer a real call, then pay. The phone reports the call (`ON_CALL`) and, for an incoming call with the caller check allowed, whether the caller is a contact saved at least 7 days ago. A call is one input to the model, not a warning on its own: payments that warn for other reasons get `ON_CALL` added to their reasons, and paying Vikram ₹25,000 stays green at most hours, with or without a call.

From a terminal, Gradle needs JDK 17 and the Android SDK, for example:

```bash
ANDROID_HOME=~/Library/Android/sdk JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home ./gradlew :app:installDebug
```

## Using the app

- **Home:** "Pay anyone" and "More" open pay by phone number; "Bank transfer" and the search bar open pay by UPI ID; tapping a person opens the amount screen. UPI Lite, Rewards and Mobile recharge are placeholders ("Not available in this demo").
- **Scan any QR code:** there is no camera in the demo. Tap a sample QR (Chai Point ₹45, CBI Cyber Cell Notice ₹48,000, Electricity Rebate ₹5,000 from WhatsApp) or "Upload from gallery" (the rebate QR).
- **UPI PIN:** any 6 digits.
- **Money tab:** transaction history. **You tab:** profile, bank accounts and, in debug builds, the **Simulation Lab**: the API address, a **custom scenario** form (any UPI ID, amount, entry channel, on a call, screen shared, new remote-access app, note) that opens the real payment screen so Pay shows the real amber, red or decline screen, and scripted scenarios scored against the API. The custom toggles apply to that one payment only.
- Satark stays invisible on normal payments. It appears only as the amber warning, the red pause or the decline screen, in English and Hindi.
- Those warning screens and the PIN pad are secure windows: screen sharing, casting, screen recording and screenshots show them black, so a scammer watching the screen cannot read the warning or see what is tapped. The user sees them normally. (On the emulator, `adb shell screencap` shows black while the warning is on the display.)
- **Ask my trusted contact** (on the red pause) opens the phone's SMS app or WhatsApp with the question already written; the user picks the contact and the reply arrives there. The pause keeps counting down meanwhile.
- **Appeals:** the amber warning offers "This was me, I know this payee": later ambers for that payee are not shown (never during a call or remote session, and not after the payee is reported again). The red pause and the decline screen offer only "Report a false alarm", which sends the case to the analyst console and changes nothing until an analyst clicks **Accept appeal**.

## Before every demo

1. Run `python scripts/reset_demo_db.py`. Seeded mule activity expires after 24 hours, each red pause holds that payment for 30 minutes, and earlier runs' payments and appeals change later checks.
2. Start the backend and check `curl http://127.0.0.1:8000/health`.
3. On a real phone, run `adb reverse tcp:8000 tcp:8000` again after reconnecting USB.
4. Open the app once after installing. The first check after a fresh install is the slowest; the app warms up its connection at launch and waits up to 2 seconds before showing the fallback warning.

Seeded journeys that work end to end (checked against a freshly reset database):

| Journey | In the app | Result |
|---|---|---|
| Friend | Home → Rahul → ₹450 | Green: no warning, PIN, receipt |
| Fake CBI notice | Scan any QR code → CBI Cyber Cell Notice → Pay | Red pause: reported payee, unusual amount, many new payers |
| KYC helpdesk | Bank transfer → `kyc-helpdesk-update@ybl` → ₹48,000 | Red pause |
| Mule account | Bank transfer → `mule.fastcash@okaxis` → ₹25,000 | Red pause |
| WhatsApp rebate QR | Scan any QR code → Electricity Rebate (or Upload from gallery) | Red pause |
| Confirmed scam account | Bank transfer → `confirmed-scam-mule@ybl` → any amount | Blocked (decline) |

A brand-new handle typed live gets a warning, not a red pause: red needs corroborating evidence about the payee.

A live call is one input to the model, not a warning on its own. Paying a known person a large amount during a call (Home → Vikram → ₹25,000) is green at most hours, with or without a call; it turns amber around 21:00, when the demo user rarely pays. A call from a contact saved at least 7 days ago makes a warning less likely; an unknown caller does not. These journeys were checked at every hour of the day against a fresh demo database. Demo-data change for the retrained model (`ml/train.py`): the seeded `electricity-rebate@oksbi` payee has 3 prior reports instead of 1.

### Results page

`http://127.0.0.1:8000/eval` shows the last logged holdout run (`ml/eval_log.md`): model only against model plus policy, recall by scam type, false alarms by group and the named failure cases. "Score a fresh world" (needs the analyst key) generates a world from any unused seed and scores it live through `ml/evaluate.py`, leak checks included. The first run on a new checkout also generates the train and holdout worlds for the leak checks (about a minute and a half); later runs take seconds. `python ml/robustness.py` re-scores a separate world (seed 101) with key simulator rates at half and double (about 10 minutes); the page shows its latest run.

### Mule caught (analyst console)

1. Open `http://127.0.0.1:8000/console` and paste the analyst key the start script printed.
2. Run the burst: 15 new payers pay `quickloan.agent@ybl` over about a minute, each through a real risk check and payment completion. The cases appear in the console as they arrive.

```bash
python scripts/mule_burst.py
```

3. Click any `quickloan.agent@ybl` case. The payee view shows the new payers in the last 24 hours and in the last 10 minutes.
4. Enter an analyst ID and click **Confirm scam**, then change the ID and confirm again: two different analysts must confirm.
5. In the app: Bank transfer → `quickloan.agent@ybl` → any amount. The payment is blocked, and the declined case shows up in the console.

**Clear** withdraws all confirmations (one analyst is enough); reports stay on record. Confirm and clear are both written to the audit log.

## Tests

```bash
PYTHONPATH=. python -m pytest api/tests -q
```

Android unit tests (with Gradle JDK 17):

```bash
./gradlew test
```

## Design

- The host app follows a stock UPI app's home screen; sizes, colours and type were measured from reference screenshots. Material 3, light theme only, Google Sans. No third-party brand names or logos.
- Satark's screens are for seniors and less confident users first: large text that follows the system font size, English and Hindi with equal weight, and the safe action always the most prominent button.

## Honest limits

- The model and thresholds come from our own simulator, not real bank data. Numbers are simulation results, not real-world accuracy.
- Screen sharing is detected only as an extra display (casting or mirroring); `device_new` and failed PIN attempts are not measured in this demo.
- Hiding warnings from screen sharing stops the scammer reading them, not noticing that one appeared (the shared screen goes dark); apps with accessibility access can still read on-screen text.
- The caller check works for incoming phone calls only: outgoing and internet (WhatsApp) calls have no number, and the check needs call-state, call-log and contacts permissions (Simulation Lab → Caller check → Allow). Without an answer the call counts as from an unknown caller. Google Play restricts call-log access, so a store release would need another way to get the number.
- On an emulator, simulate a call with `adb emu gsm call <number>` and answer it with `adb emu gsm accept <number>`.
- QR scanning is simulated (sample codes, no camera). The Simulation Lab's scripted scenarios only report Pass or Fail; use the custom scenario form to see the warning screens.
- One demo user (`raksham@oksbi`) is hard-coded in the app, and the app endpoints trust the `user_ref` they are sent: there is no user sign-in, so in this demo anyone who knows a case ID and user ID can appeal that case.
