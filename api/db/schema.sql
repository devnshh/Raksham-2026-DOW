-- SATARK Database Schema (SQLite)

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    payee_vpa TEXT NOT NULL,
    amount REAL NOT NULL,
    hour INTEGER NOT NULL,
    timestamp_ms INTEGER NOT NULL,
    typing_ms REAL DEFAULT 280.0,
    pauses INTEGER DEFAULT 0,
    pin_secs REAL DEFAULT 3.5,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_txn_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_txn_payee ON transactions(payee_vpa);
CREATE INDEX IF NOT EXISTS idx_txn_time ON transactions(timestamp_ms);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    typing_ms REAL NOT NULL,
    pauses INTEGER NOT NULL,
    pin_secs REAL NOT NULL,
    timestamp_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, timestamp_ms DESC);

CREATE TABLE IF NOT EXISTS payees (
    vpa TEXT PRIMARY KEY,
    display_name TEXT,
    first_seen_at TEXT,
    verified INTEGER DEFAULT 0,
    is_merchant INTEGER DEFAULT 0,
    name TEXT,
    is_verified_merchant BOOLEAN DEFAULT 0,
    account_age_days REAL DEFAULT 365.0,
    new_payers_24h INTEGER DEFAULT 0,
    prior_reports_count INTEGER DEFAULT 0,
    is_confirmed_scam BOOLEAN DEFAULT 0,
    confirmations TEXT DEFAULT '[]', -- JSON array of distinct analyst IDs
    category TEXT DEFAULT 'regular',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payer_id TEXT NOT NULL,
    payee_vpa TEXT NOT NULL,
    amount REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_payments_payee_time ON payments(payee_vpa, created_at);
CREATE INDEX IF NOT EXISTS idx_payments_payer ON payments(payer_id);

CREATE TABLE IF NOT EXISTS scam_registry (
    vpa TEXT PRIMARY KEY,
    report_count INTEGER DEFAULT 0,
    confirmed_at TEXT,
    source TEXT DEFAULT 'analyst'
);

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    txn_ref TEXT,
    user_id TEXT NOT NULL,
    payee_vpa TEXT NOT NULL,
    amount REAL NOT NULL,
    tier TEXT NOT NULL,
    reasons TEXT NOT NULL, -- JSON serialized list
    template_id TEXT NOT NULL,
    hold_minutes INTEGER DEFAULT 0,
    feature_vector TEXT NOT NULL, -- JSON serialized
    evidence_pack TEXT NOT NULL,  -- JSON serialized
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cases_user ON cases(user_id);
CREATE INDEX IF NOT EXISTS idx_cases_tier ON cases(tier);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence INTEGER NOT NULL UNIQUE,
    prev_hash TEXT NOT NULL,
    curr_hash TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    case_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    payee_vpa TEXT NOT NULL,
    tier TEXT NOT NULL,
    reasons TEXT NOT NULL, -- JSON serialized
    model_version TEXT NOT NULL,
    policy_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_seq ON audit_log(sequence);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    reporter_id TEXT NOT NULL,
    payee_vpa TEXT NOT NULL,
    reason TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyst_confirmations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payee_vpa TEXT NOT NULL,
    analyst_id TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL
);


-- Payees a user has vouched for on an amber warning ("This was me", source 'user') or that an
-- analyst cleared after a false-alarm report (source 'analyst'). See the policy engine for what each lowers.
CREATE TABLE IF NOT EXISTS trusted_pairs (
    user_id TEXT NOT NULL,
    payee_vpa TEXT NOT NULL,
    source TEXT NOT NULL,
    case_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, payee_vpa)
);
