-- المرحلة 1: الجداول الأساسية

CREATE TABLE users (
    user_id     INTEGER PRIMARY KEY,
    first_name  TEXT    NOT NULL DEFAULT '',
    last_name   TEXT,
    username    TEXT,
    is_bot      INTEGER NOT NULL DEFAULT 0,
    first_seen  INTEGER NOT NULL,
    last_seen   INTEGER NOT NULL
);
CREATE INDEX idx_users_username ON users (lower(username));

CREATE TABLE groups (
    chat_id     INTEGER PRIMARY KEY,
    title       TEXT    NOT NULL DEFAULT '',
    username    TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    added_by    INTEGER,
    joined_at   INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL
);

CREATE TABLE group_members (
    chat_id      INTEGER NOT NULL REFERENCES groups (chat_id) ON DELETE CASCADE,
    user_id      INTEGER NOT NULL,
    rank         INTEGER NOT NULL DEFAULT 0 CHECK (rank >= 0),
    rank_set_by  INTEGER,
    rank_set_at  INTEGER,
    msg_count    INTEGER NOT NULL DEFAULT 0 CHECK (msg_count >= 0),
    first_seen   INTEGER NOT NULL,
    last_seen    INTEGER NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
CREATE INDEX idx_members_rank ON group_members (chat_id, rank) WHERE rank > 0;

CREATE TABLE group_settings (
    chat_id     INTEGER NOT NULL REFERENCES groups (chat_id) ON DELETE CASCADE,
    key         TEXT    NOT NULL,
    value       TEXT,
    updated_by  INTEGER,
    updated_at  INTEGER NOT NULL,
    PRIMARY KEY (chat_id, key)
);

CREATE TABLE bot_settings (
    key         TEXT PRIMARY KEY,
    value       TEXT,
    updated_at  INTEGER NOT NULL
);

CREATE TABLE audit_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER,
    actor_id    INTEGER,
    target_id   INTEGER,
    action      TEXT    NOT NULL,
    details     TEXT,
    result      TEXT    NOT NULL DEFAULT 'ok',
    created_at  INTEGER NOT NULL
);
CREATE INDEX idx_audit_chat ON audit_logs (chat_id, created_at);
CREATE INDEX idx_audit_target ON audit_logs (target_id, created_at);
