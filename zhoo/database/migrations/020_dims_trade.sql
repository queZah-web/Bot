-- تجارة الأبعاد: وين التاجر، ومتى يوصل، وحدث الطريق، وسعة مخزنه
CREATE TABLE dim_state (
    chat_id    INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    dim        TEXT    NOT NULL DEFAULT 'earth',
    arrive_at  INTEGER NOT NULL DEFAULT 0,
    cap        INTEGER NOT NULL DEFAULT 10,
    event      TEXT,
    dest       TEXT,
    PRIMARY KEY (chat_id, user_id)
);

-- حمولة التاجر من الموارد
CREATE TABLE dim_cargo (
    chat_id  INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    res      TEXT    NOT NULL,
    qty      INTEGER NOT NULL CHECK (qty >= 0),
    paid     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, user_id, res)
);
