-- المرحلة 7: الخبرة والمستويات والفوز بالمسابقات

ALTER TABLE group_members ADD COLUMN xp INTEGER NOT NULL DEFAULT 0;
ALTER TABLE group_members ADD COLUMN wins INTEGER NOT NULL DEFAULT 0;
CREATE INDEX idx_members_xp ON group_members (chat_id, xp) WHERE xp > 0;
CREATE INDEX idx_members_wins ON group_members (chat_id, wins) WHERE wins > 0;

-- خبرة يومية حتى نسوي ترتيب أسبوعي وشهري
CREATE TABLE xp_daily (
    chat_id  INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    day      TEXT    NOT NULL,   -- YYYY-MM-DD (UTC)
    xp       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, user_id, day)
);
CREATE INDEX idx_xp_daily_day ON xp_daily (chat_id, day);
