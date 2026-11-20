-- المرحلة 4: التحقق من الأعضاء الجدد (يتحمل إعادة تشغيل البوت)

CREATE TABLE captcha_pending (
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    message_id  INTEGER,
    expires_at  INTEGER NOT NULL,
    created_at  INTEGER NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
CREATE INDEX idx_captcha_expiry ON captcha_pending (expires_at);
