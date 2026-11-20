-- قفل السب: سجل الرسائل المسيئة المحذوفة (يُحذف تلقائياً بعد 30 يوم)

CREATE TABLE swear_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    word        TEXT    NOT NULL,
    text        TEXT    NOT NULL,
    action      TEXT    NOT NULL CHECK (action IN ('delete', 'mute', 'ban')),
    created_at  INTEGER NOT NULL
);
CREATE INDEX idx_swear_chat ON swear_logs (chat_id, id);
CREATE INDEX idx_swear_user ON swear_logs (chat_id, user_id, id);
CREATE INDEX idx_swear_time ON swear_logs (created_at);
