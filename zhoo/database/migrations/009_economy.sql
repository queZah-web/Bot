-- المرحلة 8: الاقتصاد الافتراضي (زهرات 🌸 — نقاط افتراضية بس، مو فلوس حقيقية)

CREATE TABLE wallets (
    chat_id       INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    balance       INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    total_earned  INTEGER NOT NULL DEFAULT 0,
    streak        INTEGER NOT NULL DEFAULT 0,
    last_daily    INTEGER,
    title_item    TEXT,
    frame_item    TEXT,
    custom_title  TEXT,
    PRIMARY KEY (chat_id, user_id)
);
CREATE INDEX idx_wallets_rich ON wallets (chat_id, balance) WHERE balance > 0;

CREATE TABLE transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id        INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    amount         INTEGER NOT NULL,
    kind           TEXT    NOT NULL,
    ref            TEXT,
    balance_after  INTEGER NOT NULL,
    created_at     INTEGER NOT NULL
);
CREATE INDEX idx_tx_user ON transactions (chat_id, user_id, id);
CREATE INDEX idx_tx_kind ON transactions (chat_id, user_id, kind, created_at);

CREATE TABLE inventory (
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    item        TEXT    NOT NULL,
    created_at  INTEGER NOT NULL,
    PRIMARY KEY (chat_id, user_id, item)
);

CREATE TABLE missions (
    chat_id   INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    day       TEXT    NOT NULL,
    key       TEXT    NOT NULL,
    progress  INTEGER NOT NULL DEFAULT 0,
    done      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, user_id, day, key)
);
