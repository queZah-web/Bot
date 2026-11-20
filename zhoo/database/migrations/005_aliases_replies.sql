-- اختصارات الأوامر + الردود والردود المميزة

CREATE TABLE command_aliases (
    chat_id      INTEGER NOT NULL,
    alias        TEXT    NOT NULL,      -- موحّد
    display      TEXT    NOT NULL,      -- كما كتبه المدير
    command_key  TEXT    NOT NULL,
    created_by   INTEGER,
    created_at   INTEGER NOT NULL,
    PRIMARY KEY (chat_id, alias)
);

CREATE TABLE replies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    trigger     TEXT    NOT NULL,       -- موحّد
    display     TEXT    NOT NULL,
    special     INTEGER NOT NULL DEFAULT 0,
    created_by  INTEGER,
    created_at  INTEGER NOT NULL,
    UNIQUE (chat_id, trigger, special)
);
CREATE INDEX idx_replies_chat ON replies (chat_id, special);

CREATE TABLE reply_items (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    reply_id  INTEGER NOT NULL REFERENCES replies (id) ON DELETE CASCADE,
    position  INTEGER NOT NULL,
    kind      TEXT    NOT NULL,
    file_id   TEXT,
    text      TEXT
);
CREATE INDEX idx_reply_items ON reply_items (reply_id, position);
