-- صلاحيات مخصصة لكل شخص + قائمة المنع

CREATE TABLE member_perms (
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    allow       TEXT    NOT NULL DEFAULT '',   -- صلاحيات مضافة (مفصولة بفواصل)
    deny        TEXT    NOT NULL DEFAULT '',   -- صلاحيات مسحوبة
    updated_by  INTEGER,
    updated_at  INTEGER NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);

-- قائمة المنع: ملصق/متحركة/صورة/فيديو/كلمة ممنوعة بالمجموعة
CREATE TABLE filters (
    chat_id     INTEGER NOT NULL,
    kind        TEXT    NOT NULL CHECK (kind IN ('sticker', 'animation', 'photo', 'video', 'word')),
    value       TEXT    NOT NULL,
    label       TEXT    NOT NULL DEFAULT '',
    added_by    INTEGER,
    created_at  INTEGER NOT NULL,
    PRIMARY KEY (chat_id, kind, value)
);
