-- المرحلة 3: العقوبات والتحذيرات

CREATE TABLE punishments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    kind        TEXT    NOT NULL CHECK (kind IN ('ban', 'kick', 'mute', 'restrict')),
    actor_id    INTEGER,
    reason      TEXT,
    until       INTEGER,            -- NULL = دائم
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  INTEGER NOT NULL,
    lifted_at   INTEGER,
    lifted_by   INTEGER
);
CREATE INDEX idx_pun_member ON punishments (chat_id, user_id, created_at);
CREATE INDEX idx_pun_active ON punishments (chat_id, kind) WHERE active = 1;
CREATE INDEX idx_pun_expiry ON punishments (until) WHERE active = 1 AND until IS NOT NULL;

CREATE TABLE warnings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    actor_id    INTEGER,
    reason      TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  INTEGER NOT NULL
);
CREATE INDEX idx_warn_member ON warnings (chat_id, user_id) WHERE active = 1;
