-- التقييم صار عام (بكل المجموعات): تقييم واحد من كل شخص لكل شخص، ينحفظ بملفه.
-- نجمع التقييمات القديمة تحت chat_id = 0، والأحدث يغلب إذا نفس الشخص قيّم بأكثر من مجموعة.
INSERT OR REPLACE INTO ratings (chat_id, target_id, rater_id, vibe, score, updated_at)
    SELECT 0, target_id, rater_id, vibe, score, updated_at FROM ratings WHERE chat_id != 0 ORDER BY updated_at;
DELETE FROM ratings WHERE chat_id != 0;
CREATE INDEX idx_thanks_global ON thanks (to_id);
