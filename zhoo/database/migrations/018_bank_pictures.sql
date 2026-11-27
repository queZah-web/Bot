-- صور لعبة «صور» المضافة: scope = 0 لكل المجموعات (المطور)، أو ايدي المجموعة (المالك وفوگ)
CREATE TABLE game_pictures (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scope       INTEGER NOT NULL,
    file_id     TEXT    NOT NULL,
    key         TEXT    NOT NULL,       -- أول اسم موحّد (للمسح)
    answers     TEXT    NOT NULL,       -- الأسماء المقبولة مفصولة بـ |
    created_by  INTEGER,
    created_at  INTEGER NOT NULL
);
CREATE INDEX idx_game_pictures_scope ON game_pictures (scope, key);

-- بنك زهو: الحساب البنكي (الفلوس بالبنك محمية من الزرف) + أوقات الانتظار
CREATE TABLE bank_accounts (
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    account_no  TEXT    NOT NULL,
    card        TEXT    NOT NULL,
    balance     INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    created_at  INTEGER NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE bank_cooldowns (
    chat_id  INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    key      TEXT    NOT NULL,
    until    INTEGER NOT NULL,
    PRIMARY KEY (chat_id, user_id, key)
);
