-- المرحلة 6: التفاعل الاجتماعي

ALTER TABLE users ADD COLUMN bio TEXT;

CREATE TABLE thanks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    from_id     INTEGER NOT NULL,
    to_id       INTEGER NOT NULL,
    created_at  INTEGER NOT NULL
);
CREATE INDEX idx_thanks_to ON thanks (chat_id, to_id);
CREATE INDEX idx_thanks_pair ON thanks (chat_id, from_id, to_id, created_at);

CREATE TABLE suggestions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    text        TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'review', 'accepted', 'rejected')),
    decided_by  INTEGER,
    decided_at  INTEGER,
    created_at  INTEGER NOT NULL
);
CREATE INDEX idx_sugg_chat ON suggestions (chat_id, id);

CREATE TABLE suggestion_votes (
    suggestion_id  INTEGER NOT NULL REFERENCES suggestions (id) ON DELETE CASCADE,
    user_id        INTEGER NOT NULL,
    vote           INTEGER NOT NULL CHECK (vote IN (-1, 1)),
    PRIMARY KEY (suggestion_id, user_id)
);

CREATE TABLE complaints (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    text        TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    closed_by   INTEGER,
    closed_at   INTEGER,
    created_at  INTEGER NOT NULL
);
CREATE INDEX idx_complaints_chat ON complaints (chat_id, status, id);

-- كل ثنائي ينخزن بصفين (لكل طرف صف) حتى البحث يكون سريع
CREATE TABLE partners (
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    partner_id  INTEGER NOT NULL,
    hidden      INTEGER NOT NULL DEFAULT 0,
    since       INTEGER NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
