-- ردود زهو المضافة: scope = 0 لكل المجموعات (المطور)، أو ايدي المجموعة (المالك وفوگ).
-- الكلمة الوحدة يصير إلها أكثر من رد، وزهو تختار وحد عشوائي بدون ما تكرر نفس الرد ورا بعض.
CREATE TABLE zhoo_replies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scope       INTEGER NOT NULL,
    trigger     TEXT    NOT NULL,       -- موحّد
    display     TEXT    NOT NULL,       -- مثل ما انكتب
    reply       TEXT    NOT NULL,
    created_by  INTEGER,
    created_at  INTEGER NOT NULL
);
CREATE INDEX idx_zhoo_replies_scope ON zhoo_replies (scope, trigger);
