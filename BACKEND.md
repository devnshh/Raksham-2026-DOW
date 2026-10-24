# SATARK Backend Architecture & API Guide
**Track 02: AI-Driven Scam Pattern Recognition (RAKSHAM Hackathon)**

---

## 1. Overview

**Satark** is a real-time scam-interruption layer designed to sit inside UPI applications (such as Google Pay, PhonePe, Paytm, or BHIM). It detects when an authorized UPI payment is being coached by a scammer (via phone call, screen sharing, or remote desktop control) to an unverified or mule beneficiary, and intervenes with a proportionate, explained pause rather than a blind block.

The backend service is built with **Python 3.10+**, **FastAPI**, **Pydantic v2**, and **SQLite (with WAL mode)**. The feature store is decoupled behind an abstract interface (`BaseFeatureStore`), allowing production deployment with Redis without modifying application logic.

---

## 2. Target Architecture & Execution

### Service Decoupling
```
 Android App / Client
          │
          ▼  (Port 8000)
┌────────────────────────────────────────────────────────┐
│  Satark Risk API (api/)                                │
│  - Analyst API key on /v1/cases, /v1/payees, /internal │
│    (no rate limiting yet)                              │
│  - Feature Builder & Feature Store (SQLite WAL)        │
│  - Policy Engine (Gate, Tiering, Corroboration)        │
│  - Append-Only Hash-Chained Audit Log                  │
│  - ModelClient (HttpModelClient / LocalModelClient)    │
└────────────────────────────────────────────────────────┘
          │  (Internal API Key: X-Internal-Key)
          ▼  (Port 8001)
┌────────────────────────────────────────────────────────┐
│  Satark Model Service (model_service/)                 │
│  - Loads SatarkScorer & XGBoost fusion bundle once     │
│  - GET /health (Readiness probe)                       │
│  - POST /score (Inference & SHAP reason extraction)    │
│  - Rejects missing required features with HTTP 422     │
└────────────────────────────────────────────────────────┘
```

### Setup (once)

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` pins `scikit-learn==1.8.0` and `xgboost==3.2.0`, the versions the trained bundle was saved with. Other scikit-learn versions fail to load the note-intent model, and every scored payment then falls back to amber `CHECK_UNAVAILABLE`.

### Reset the demo database (before every demo)

```bash
python scripts/reset_demo_db.py
```

The database is local state and is not committed. It is created and seeded on first start; the reset script wipes and re-seeds it. Re-seed before a demo: seeded mule fan-in ages out after 24 hours, and earlier runs' payments, appeals and holds change later checks.

### Starting Both Services Together (Recommended)

```bash
# macOS / Linux:
scripts/start_all.sh

# Windows PowerShell:
powershell -File scripts/start_all.ps1
# Windows Command Prompt:
scripts\start_all.bat
```

The scripts generate a random `MODEL_SERVICE_KEY` (shared by both services) and `SATARK_ANALYST_KEY` for each run unless you set them, and print the analyst key. No key is hard-coded anywhere.
This script:
1. Checks port 8001; if free, launches `model_service` on port 8001.
2. Polls `GET http://127.0.0.1:8001/health` until HTTP 200 is returned.
3. Checks port 8000; if free, launches `api` on port 8000 configured with `MODEL_SERVICE_URL=http://127.0.0.1:8001`.

### Starting Services Separately

**1. Model Service (Port 8001):**
```bash
export MODEL_SERVICE_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
python -m uvicorn model_service.main:app --host 127.0.0.1 --port 8001
```

**2. Risk API (Port 8000):**
```powershell
# With external Model Service:
$env:MODEL_SERVICE_URL = "http://127.0.0.1:8001"
$env:MODEL_SERVICE_KEY = "<same value the Model Service was started with>"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Or in standalone in-process mode (LocalModelClient):
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running Test Suite
Execute the full pytest test suite (58 unit, journey, model service and regression tests):

```powershell
$env:PYTHONPATH = "."
python -m pytest api/tests -v
```

### Latency Benchmarks (205 Requests)
| Mode | Target | Mean | p50 | p95 |
|---|---|---|---|---|
| **LocalModelClient (In-Process)** | < 150 ms | 22.60 ms | 22.94 ms | **24.96 ms** |
| **HttpModelClient (HTTP Service)** | < 150 ms | 35.13 ms | 36.02 ms | **42.75 ms** |

---

## 3. API Contract & Endpoints (with `curl` Examples)

### 1. Real-Time Risk Assessment
- **Endpoint**: `POST /v1/risk/assess`
- **Strict Contract Rule**: Returns **ONLY** `{tier, reasons[], template_id, hold_minutes, case_id}`. Internal risk scores, feature vectors, and model weights are **never** returned to client apps.

#### Scenario A: Silent Pass (Demo Journey 1)
Payment to a regular friend (`rahul.sharma@oksbi`) for ₹450 with no coercion signals.

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/v1/risk/assess \
  -H "Content-Type: application/json" \
  -d '{
    "txn_ref": "t-001001",
    "user_ref": "raksham@oksbi",
    "payee_vpa": "rahul.sharma@oksbi",
    "amount": 450.0,
    "entry_channel": "typed_vpa",
    "session": {
      "on_call": false,
      "screen_shared": false,
      "remote_app_present": false,
      "remote_app_new": false,
      "app_switches": 0,
      "typing_ms": 280.0,
      "pauses": 0,
      "pin_secs": 3.2,
      "device_new": false
    },
    "context": {
      "note_text": "dinner split"
    }
  }'
```

**Response:**
```json
{
  "tier": "green",
  "reasons": [],
  "template_id": "green_silent_pass",
  "hold_minutes": 0,
  "case_id": "c-47a19c3b"
}
```

---

#### Scenario B: Red Smart Pause (Demo Journey 2)
Victim coerced via active phone call into transferring ₹48,000 to an unverified brand look-alike handle (`kyc-helpdesk-update@ybl`). Corroboration rule fires: Family A (on_call) + Family B (young lookalike payee).

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/v1/risk/assess \
  -H "Content-Type: application/json" \
  -d '{
    "txn_ref": "t-001002",
    "user_ref": "raksham@oksbi",
    "payee_vpa": "kyc-helpdesk-update@ybl",
    "amount": 48000.0,
    "entry_channel": "typed_vpa",
    "session": {
      "on_call": true,
      "screen_shared": false,
      "remote_app_present": false,
      "remote_app_new": false,
      "app_switches": 3,
      "typing_ms": 420.0,
      "pauses": 3,
      "pin_secs": 8.5,
      "device_new": false
    },
    "context": {
      "note_text": "kyc verification fee"
    }
  }'
```

**Response:**
```json
{
  "tier": "red",
  "reasons": [
    "ON_CALL",
    "NEW_PAYEE_YOUNG_ACCOUNT",
    "LOOKALIKE_HANDLE"
  ],
  "template_id": "red_call_new_payee_v1",
  "hold_minutes": 30,
  "case_id": "c-89b21f0a"
}
```

---

#### Scenario C: Decline on Confirmed Scam Mule (Demo Journey 3)
Attempting transfer to an analyst-confirmed fraudulent account (`confirmed-scam-mule@ybl`).

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/v1/risk/assess \
  -H "Content-Type: application/json" \
  -d '{
    "txn_ref": "t-001003",
    "user_ref": "raksham@oksbi",
    "payee_vpa": "confirmed-scam-mule@ybl",
    "amount": 2000.0,
    "session": { "on_call": false }
  }'
```

**Response:**
```json
{
  "tier": "decline",
  "reasons": [
    "ANALYST_CONFIRMED_SCAM"
  ],
  "template_id": "decline_known_mule_v1",
  "hold_minutes": 0,
  "case_id": "c-12f38d90"
}
```

---

### 2. Dual Analyst Confirmation for Scam Payees
- **Endpoint**: `POST /v1/payees/{vpa}/confirm`
- **Rule**: Requires **TWO DISTINCT** analyst IDs before marking `is_confirmed_scam = true`.

**Step 1: First Analyst Confirms:**
```bash
curl -X POST http://127.0.0.1:8000/v1/payees/mule-account@ybl/confirm \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SATARK_ANALYST_KEY" \
  -d '{
    "analyst_id": "analyst_alpha",
    "notes": "Reported by cybercell for investment fraud"
  }'
```
*Output: `status: "pending_second_analyst"`, `total_confirmations: 1`, `is_confirmed_scam: false`*

**Step 2: Second Analyst Confirms:**
```bash
curl -X POST http://127.0.0.1:8000/v1/payees/mule-account@ybl/confirm \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SATARK_ANALYST_KEY" \
  -d '{
    "analyst_id": "analyst_beta",
    "notes": "Verified fan-in transaction logs"
  }'
```
*Output: `status: "analyst_confirmed_scam"`, `total_confirmations: 2`, `is_confirmed_scam: true`*

---

### 3. User Scam Reporting
- **Endpoint**: `POST /v1/report`

```bash
curl -X POST http://127.0.0.1:8000/v1/report \
  -H "Content-Type: application/json" \
  -d '{
    "reporter_id": "raksham@oksbi",
    "payee_vpa": "fake-cbi-fund@okaxis",
    "reason": "Digital arrest scam call",
    "notes": "Caller pretended to be Delhi Police cyber unit"
  }'
```

---

### 4. Case Management & Security Evidence Packs
- **List Cases**: `GET /v1/cases?tier=red&limit=10`
- **Evidence Pack**: `GET /v1/cases/{case_id}`

```bash
curl -s -H "X-API-Key: $SATARK_ANALYST_KEY" http://127.0.0.1:8000/v1/cases/c-89b21f0a | python3 -m json.tool
```
*Returns full feature vector, reason breakdown, family contributions, applied policy rules, and SHA-256 audit block hash for dispute resolution and 1930/cybercrime.gov.in prefilling.*

---

### 4b. Red-tier Questionnaire (app, no analyst key)
- **Endpoint**: `POST /v1/risk/{case_id}/questionnaire` with `{"user_ref": "...", "answers": {"is_anyone_guiding_you": true}}`
- Attaches the answer to the existing case. Answers can only raise the tier (amber to red); they never lower it.

### 4c. Payment Completion (app, no analyst key)
- **Endpoint**: `POST /v1/payments/complete` with `{case_id, user_ref, payee_vpa, amount, typing_ms?, pauses?, pin_secs?}`
- Called after the PIN succeeds. Only completed payments update the user's baseline, first-time status and payee fan-in; a risk check alone records nothing.
- Refused for declined cases (403) and for red cases whose hold has not elapsed (409).

### 5. Policy & Threshold Inspection
- **Endpoint**: `GET /v1/policy`

```bash
curl -s http://127.0.0.1:8000/v1/policy | python3 -m json.tool
```

---

### 6. System Health & Cryptographic Audit Verification
- **Endpoint**: `GET /health`

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
```
*Output: Verifies database connectivity and runs full cryptographic integrity verification of the hash-chained audit log.*

---

## 4. Policy Engine Decision Architecture

The policy engine (`api/policy/engine.py`) is written in pure Python with zero framework dependencies. It enforces decisions in strict priority order:

```
[ Incoming Risk Request ]
           │
           ▼
1. Analyst-Confirmed Scam? ────────► (YES) ──► DECLINE (with appeal path)
           │ (NO)
           ▼
2. Trusted Payee Rule ─────────────► (YES) ──► Has Family A (Coercion)?
   (3+ txns over 30+ days)                         ├──► (NO)  ──► GREEN (Silent Pass)
                                                   └──► (YES) ──► Bypass Exemption (Go to step 3)
           │
           ▼
3. Eligibility Gate ───────────────► (NO)  ──► GREEN (Silent Pass)
   (First-time payee OR amount_ratio >= 2.0 OR lookalike >= 0.70 OR Family A active)
           │ (YES)
           ▼
4. Scorer Execution (Stub / XGBoost)
   (Fails open with device-only checks if timeout > 300ms or error occurs)
           │
           ▼
5. Tier
   ├── RED:   score >= red threshold AND >= 2 independent families firing ──► RED (30-min hold)
   ├── AMBER: score >= amber threshold, OR screen share / new remote app
   │          (two families alone no longer warn: on validation that rule raised ~15,900 false alarms for 1 extra scam)
   └── GREEN: otherwise
   Family A counts a call at full weight only when the caller is not a contact saved 7+ days ago.
           │
           ▼
6. Vouched-for payee ("This was me" on amber, or an analyst-accepted appeal) can lower later warnings
   (never during a call or remote session; there is no weekly warning cap any more)
           │
           ▼
7. Red-Tier Questionnaire
   (Can only RAISE risk or add reasons; NEVER lowers an existing RED tier)
```

---

## 5. Append-Only Cryptographic Audit Log

Every risk assessment is permanently recorded in an append-only, SHA-256 hash-chained log (`api/store/audit_store.py`):
- **Genesis Block**: Sequence 1 points to `0` $\times 64$.
- **Chain Invariant**: Row $N$ contains `curr_hash = SHA256(sequence | prev_hash | timestamp | case_id | user_id | payee_vpa | tier | sorted_reasons | model_version | policy_version)`.
- **Tamper Detection**: If any row or historical parameter is altered in SQLite, `verify_chain()` detects the signature mismatch and pinpoints the corrupted row sequence.

---

## 6. SDK vs. API Contract Mismatches & Solutions

Historical note: the old `satark-sdk` module has been removed; the app now uses `risk-sdk`. During review of that SDK we identified four architectural mismatches with the Section 17 API contract:

| # | Contract Dimension | Current SDK Behavior (`satark-sdk`) | Section 17 API Specification | Solution / Fix |
|---|---|---|---|---|
| **1** | **Feature Computation** | Computes baseline features (`amount_ratio`, `amount_z`) and session z-scores locally on-device. | Server is the ground truth. Client sends only raw telemetry (`typing_ms`, `pauses`, `pin_secs`, `on_call`, `amount`); server computes derived features. | API accepts raw signals via `SessionSignals` and computes point-in-time statistics against SQLite historical stores. |
| **2** | **Response Content** | Exposes internal `score`, `familyFlags`, and full `featureVector` to the client app. | **STRICT PRIVACY RULE**: Response must contain **ONLY** `{tier, reasons, template_id, hold_minutes, case_id}`. Score and weights are never returned. | API response model strictly restricts fields. Client UI resolves headline/explanation text locally via `template_id` and reason codes. |
| **3** | **User Identification** | `evaluateRisk(...)` assumes an implicit single local user profile without passing a user ID. | Server requires `user_ref` / `user_id` to query historical transaction distributions and enforce the 7-day Amber cap. | `RiskAssessmentRequest` accepts `user_ref` (defaulting to `"default_user"` if omitted for backwards compatibility). |
| **4** | **Questionnaire Feedback** | Client UI does not pass interactive questionnaire responses to backend. | `POST /v1/risk/assess` accepts optional `questionnaire_answers` to dynamically elevate risk. | Added `questionnaire_answers: Optional[dict[str, Any]]` to API schema with rule that answers can only raise risk. |

---

## 7. Data and Privacy Rules (enforced in code)

- **Note text never leaves the phone.** The app sends only `note_intent` (risk-sdk `NoteIntent.kt`). If an old client sends `note_text`, the server derives the intent and discards the text; it is never stored or scored.
- **Unknown is unknown.** A payee we have not seen before has unknown account age (`payee_age_known=false`): the model gets a neutral value and no "young account" reason is shown. Unmeasured typing or pause values score as no evidence; PIN time is ignored at risk-check time because the check runs before the PIN screen.
- **Reasons are only shown when true.** A model reason is shown only if that feature is actually in its risky state (e.g. no `QR_ENTRY` for a typed UPI ID).
- **Reports count once per reporter, weighted by the reporter's history**: full weight once the account is 30 days old with 5 completed payments, proportionally less before that, and all newer accounts together add at most half a report. Twenty brand-new accounts reporting an honest merchant do not flag it. Analyst/registry counts are kept separate and unweighted.
- **Thresholds** in `model_service/models/thresholds.json` were set on a separate validation world (simulator seed 33), not on the test world. Simulation only.
