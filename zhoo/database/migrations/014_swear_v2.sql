-- فلتر السب المتقدم: قاموس دائم بمستويات + استثناءات + سجل مخالفات أدق

-- كلمات وعبارات السب: chat_id = 0 يعني قاموس عام لكل المجموعات (من المطور)
CREATE TABLE swear_words (
    chat_id     INTEGER NOT NULL,
    norm        TEXT    NOT NULL,          -- الصيغة الموحدة (العبارة بمسافات)
    word        TEXT    NOT NULL,          -- مثل ما انكتبت
    level       INTEGER NOT NULL CHECK (level BETWEEN 1 AND 3),
    added_by    INTEGER,
    created_at  INTEGER NOT NULL,
    PRIMARY KEY (chat_id, norm)
);

-- كلمات مسموحة (استثناءات) لكل مجموعة
CREATE TABLE swear_allow (
    chat_id     INTEGER NOT NULL,
    norm        TEXT    NOT NULL,
    word        TEXT    NOT NULL,
    added_by    INTEGER,
    created_at  INTEGER NOT NULL,
    PRIMARY KEY (chat_id, norm)
);

-- سجل المخالفات: نضيف المستوى والمدة، ونوسع أنواع الإجراء (تحذير + مؤقت)
CREATE TABLE swear_logs_v2 (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    word        TEXT    NOT NULL,
    text        TEXT    NOT NULL,
    level       INTEGER NOT NULL DEFAULT 2,
    action      TEXT    NOT NULL CHECK (action IN ('delete', 'warn', 'mute', 'ban')),
    duration    INTEGER,                   -- بالثواني، NULL = دائم
    created_at  INTEGER NOT NULL
);
INSERT INTO swear_logs_v2 (id, chat_id, user_id, word, text, action, created_at)
    SELECT id, chat_id, user_id, word, text, action, created_at FROM swear_logs;
DROP TABLE swear_logs;
ALTER TABLE swear_logs_v2 RENAME TO swear_logs;
CREATE INDEX idx_swear_chat ON swear_logs (chat_id, id);
CREATE INDEX idx_swear_user ON swear_logs (chat_id, user_id, created_at);
CREATE INDEX idx_swear_time ON swear_logs (created_at);
