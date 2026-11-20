-- يوتيوب: نحفظ معرف الملف بتيليجرام حتى الطلب المكرر ينرسل فوراً بدون تحميل
CREATE TABLE yt_cache (
    video_id    TEXT PRIMARY KEY,
    file_id     TEXT NOT NULL,
    title       TEXT,
    duration    INTEGER,
    created_at  INTEGER NOT NULL
);
