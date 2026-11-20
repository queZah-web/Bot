-- تقييم الأعضاء داخل كل مجموعة: انطباع (جميل/سيئ) + درجة من 10

CREATE TABLE ratings (
    chat_id     INTEGER NOT NULL,
    target_id   INTEGER NOT NULL,
    rater_id    INTEGER NOT NULL,
    vibe        INTEGER CHECK (vibe IN (-1, 1)),
    score       INTEGER CHECK (score BETWEEN 1 AND 10),
    updated_at  INTEGER NOT NULL,
    PRIMARY KEY (chat_id, target_id, rater_id)
);
CREATE INDEX idx_ratings_target ON ratings (chat_id, target_id);
