-- المرحلة 10: استهلاك الذكاء الاصطناعي (للحدود اليومية وحساب التكلفة)
CREATE TABLE ai_usage (
    day            TEXT    NOT NULL,   -- YYYY-MM-DD (UTC)
    chat_id        INTEGER NOT NULL,
    requests       INTEGER NOT NULL DEFAULT 0,
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, chat_id)
);
