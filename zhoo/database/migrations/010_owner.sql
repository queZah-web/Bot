-- المرحلة 9: نعرف منو بدأ محادثة ويا البوت بالخاص (حتى الإذاعة توصله)
ALTER TABLE users ADD COLUMN started INTEGER NOT NULL DEFAULT 0;
CREATE INDEX idx_users_started ON users (started) WHERE started = 1;
