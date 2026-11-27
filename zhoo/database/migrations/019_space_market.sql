-- الكون: ملكية الكواكب لكل مجموعة (الكواكب نفسها تتولّد من رقمها، ما تنخزن)
CREATE TABLE space_planets (
    chat_id     INTEGER NOT NULL,
    galaxy      INTEGER NOT NULL,
    idx         INTEGER NOT NULL,
    owner_id    INTEGER NOT NULL,
    paid        INTEGER NOT NULL,
    bought_at   INTEGER NOT NULL,
    listed      INTEGER,            -- سعر العرض بسوق اللاعبين (NULL = مو معروض)
    PRIMARY KEY (chat_id, galaxy, idx)
);
CREATE INDEX idx_space_owner ON space_planets (chat_id, owner_id);
CREATE INDEX idx_space_listed ON space_planets (chat_id, listed) WHERE listed IS NOT NULL;

-- سوق الممتلكات: سيارات، عقارات، يخوت، مجوهرات، شركات
CREATE TABLE assets (
    chat_id   INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    item      TEXT    NOT NULL,
    qty       INTEGER NOT NULL CHECK (qty >= 0),
    paid      INTEGER NOT NULL DEFAULT 0,     -- مجموع اللي دفعه (لحساب الربح)
    PRIMARY KEY (chat_id, user_id, item)
);
