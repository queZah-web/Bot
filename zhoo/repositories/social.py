"""بيانات التفاعل الاجتماعي: النبذة، الشكر، الاقتراحات، الشكاوى، الثنائيات."""
from __future__ import annotations

from zhoo.database.db import Database, now


class SocialRepo:
    def __init__(self, db: Database):
        self.db = db

    # ── النبذة ──
    async def get_bio(self, user_id: int) -> str | None:
        return await self.db.fetchval("SELECT bio FROM users WHERE user_id = ?", (user_id,))

    async def set_bio(self, user_id: int, bio: str | None) -> None:
        await self.db.execute("UPDATE users SET bio = ? WHERE user_id = ?", (bio, user_id))

    # ── الشكر (عام: ينحسب من كل المجموعات وينحفظ بملف الشخص) ──
    async def last_thanks(self, chat_id: int, from_id: int, to_id: int) -> int | None:
        return await self.db.fetchval(
            "SELECT MAX(created_at) FROM thanks WHERE from_id = ? AND to_id = ?", (from_id, to_id))

    async def thanks_given_since(self, chat_id: int, from_id: int, seconds: int) -> int:
        return await self.db.fetchval(
            "SELECT COUNT(*) FROM thanks WHERE chat_id = ? AND from_id = ? AND created_at > ?",
            (chat_id, from_id, now() - seconds), default=0)

    async def add_thanks(self, chat_id: int, from_id: int, to_id: int) -> int:
        async with self.db.transaction() as conn:
            await conn.execute("INSERT INTO thanks (chat_id, from_id, to_id, created_at) VALUES (?, ?, ?, ?)",
                               (chat_id, from_id, to_id, now()))
            cur = await conn.execute("SELECT COUNT(*) FROM thanks WHERE to_id = ?", (to_id,))
            return (await cur.fetchone())[0]

    async def thanks_count(self, chat_id: int, user_id: int) -> int:
        return await self.db.fetchval("SELECT COUNT(*) FROM thanks WHERE to_id = ?", (user_id,), default=0)

    async def top_thanked(self, chat_id: int, limit: int = 10):
        return await self.db.fetchall(
            "SELECT t.to_id AS user_id, COUNT(*) AS n, u.first_name, u.last_name FROM thanks t "
            "LEFT JOIN users u ON u.user_id = t.to_id "
            "GROUP BY t.to_id ORDER BY n DESC LIMIT ?", (limit,))

    # ── الاقتراحات ──
    async def add_suggestion(self, chat_id: int, user_id: int, text: str) -> int:
        async with self.db.transaction() as conn:
            cur = await conn.execute(
                "INSERT INTO suggestions (chat_id, user_id, text, created_at) VALUES (?, ?, ?, ?)",
                (chat_id, user_id, text, now()))
            return cur.lastrowid

    async def get_suggestion(self, sid: int):
        return await self.db.fetchone(
            "SELECT s.*, u.first_name, u.last_name FROM suggestions s "
            "LEFT JOIN users u ON u.user_id = s.user_id WHERE s.id = ?", (sid,))

    async def last_suggestion_at(self, chat_id: int, user_id: int) -> int | None:
        return await self.db.fetchval("SELECT MAX(created_at) FROM suggestions WHERE chat_id = ? AND user_id = ?",
                                      (chat_id, user_id))

    async def vote(self, sid: int, user_id: int, vote: int) -> int:
        """يسجل/يغير/يلغي الصوت. يرجع الصوت الحالي (0 = انلغى)."""
        async with self.db.transaction() as conn:
            cur = await conn.execute("SELECT vote FROM suggestion_votes WHERE suggestion_id = ? AND user_id = ?",
                                     (sid, user_id))
            row = await cur.fetchone()
            if row is not None and row[0] == vote:
                await conn.execute("DELETE FROM suggestion_votes WHERE suggestion_id = ? AND user_id = ?",
                                   (sid, user_id))
                return 0
            await conn.execute(
                "INSERT INTO suggestion_votes (suggestion_id, user_id, vote) VALUES (?, ?, ?) "
                "ON CONFLICT (suggestion_id, user_id) DO UPDATE SET vote = excluded.vote", (sid, user_id, vote))
            return vote

    async def votes(self, sid: int) -> tuple[int, int]:
        row = await self.db.fetchone(
            "SELECT COALESCE(SUM(vote = 1), 0), COALESCE(SUM(vote = -1), 0) FROM suggestion_votes "
            "WHERE suggestion_id = ?", (sid,))
        return int(row[0]), int(row[1])

    async def set_suggestion_status(self, sid: int, status: str, by: int) -> None:
        await self.db.execute("UPDATE suggestions SET status = ?, decided_by = ?, decided_at = ? WHERE id = ?",
                              (status, by, now(), sid))

    async def recent_suggestions(self, chat_id: int, limit: int = 10):
        return await self.db.fetchall(
            "SELECT s.id, s.text, s.status, s.user_id, u.first_name, u.last_name, "
            "COALESCE((SELECT SUM(vote = 1) FROM suggestion_votes v WHERE v.suggestion_id = s.id), 0) AS up, "
            "COALESCE((SELECT SUM(vote = -1) FROM suggestion_votes v WHERE v.suggestion_id = s.id), 0) AS down "
            "FROM suggestions s LEFT JOIN users u ON u.user_id = s.user_id "
            "WHERE s.chat_id = ? ORDER BY s.id DESC LIMIT ?", (chat_id, limit))

    # ── الشكاوى ──
    async def add_complaint(self, chat_id: int, user_id: int, text: str) -> int:
        async with self.db.transaction() as conn:
            cur = await conn.execute("INSERT INTO complaints (chat_id, user_id, text, created_at) VALUES (?, ?, ?, ?)",
                                     (chat_id, user_id, text, now()))
            return cur.lastrowid

    async def get_complaint(self, cid: int):
        return await self.db.fetchone(
            "SELECT c.*, u.first_name, u.last_name FROM complaints c "
            "LEFT JOIN users u ON u.user_id = c.user_id WHERE c.id = ?", (cid,))

    async def last_complaint_at(self, chat_id: int, user_id: int) -> int | None:
        return await self.db.fetchval("SELECT MAX(created_at) FROM complaints WHERE chat_id = ? AND user_id = ?",
                                      (chat_id, user_id))

    async def close_complaint(self, cid: int, by: int) -> bool:
        n = await self.db.execute(
            "UPDATE complaints SET status = 'closed', closed_by = ?, closed_at = ? WHERE id = ? AND status = 'open'",
            (by, now(), cid))
        return n > 0

    async def open_complaints(self, chat_id: int, limit: int = 15):
        return await self.db.fetchall(
            "SELECT c.*, u.first_name, u.last_name FROM complaints c LEFT JOIN users u ON u.user_id = c.user_id "
            "WHERE c.chat_id = ? AND c.status = 'open' ORDER BY c.id DESC LIMIT ?", (chat_id, limit))

    # ── الثنائيات ──
    async def partner_of(self, chat_id: int, user_id: int):
        return await self.db.fetchone(
            "SELECT p.partner_id, p.hidden, p.since, u.first_name, u.last_name FROM partners p "
            "LEFT JOIN users u ON u.user_id = p.partner_id WHERE p.chat_id = ? AND p.user_id = ?", (chat_id, user_id))

    async def link(self, chat_id: int, a: int, b: int) -> bool:
        """يربط الطرفين ذرياً. يرجع False إذا واحد منهم صار مرتبط بهالأثناء."""
        ts = now()
        async with self.db.transaction() as conn:
            cur = await conn.execute("SELECT 1 FROM partners WHERE chat_id = ? AND user_id IN (?, ?)", (chat_id, a, b))
            if await cur.fetchone():
                return False
            await conn.executemany("INSERT INTO partners (chat_id, user_id, partner_id, since) VALUES (?, ?, ?, ?)",
                                   [(chat_id, a, b, ts), (chat_id, b, a, ts)])
            return True

    async def unlink(self, chat_id: int, user_id: int) -> int | None:
        """يفك الارتباط ويرجع ايدي الشريك السابق."""
        async with self.db.transaction() as conn:
            cur = await conn.execute("SELECT partner_id FROM partners WHERE chat_id = ? AND user_id = ?",
                                     (chat_id, user_id))
            row = await cur.fetchone()
            if row is None:
                return None
            await conn.execute("DELETE FROM partners WHERE chat_id = ? AND user_id IN (?, ?)",
                               (chat_id, user_id, row[0]))
            return row[0]

    async def set_hidden(self, chat_id: int, user_id: int, hidden: bool) -> bool:
        row = await self.partner_of(chat_id, user_id)
        if row is None:
            return False
        await self.db.execute("UPDATE partners SET hidden = ? WHERE chat_id = ? AND user_id IN (?, ?)",
                              (int(hidden), chat_id, user_id, row["partner_id"]))
        return True

    async def list_pairs(self, chat_id: int, limit: int = 30):
        return await self.db.fetchall(
            "SELECT p.user_id, p.partner_id, p.since, a.first_name AS a_name, b.first_name AS b_name "
            "FROM partners p LEFT JOIN users a ON a.user_id = p.user_id LEFT JOIN users b ON b.user_id = p.partner_id "
            "WHERE p.chat_id = ? AND p.user_id < p.partner_id AND p.hidden = 0 ORDER BY p.since DESC LIMIT ?",
            (chat_id, limit))


GLOBAL = 0   # التقييم عام: ينحفظ بملف الشخص ويطلع بكل المجموعات


class RatingsRepo:
    """كل شخص يقيّم الثاني مرة وحدة بكل المجموعات (ويگدر يغيّر تقييمه).

    باراميتر chat_id باقي للتوافق، بس التخزين دائماً عام.
    """

    def __init__(self, db: Database):
        self.db = db

    async def set_vibe(self, chat_id: int, target_id: int, rater_id: int, vibe: int) -> int:
        """يرجع الانطباع الحالي بعد الضغط (0 = انلغى لأنه ضغط نفس الزر)."""
        async with self.db.transaction() as conn:
            cur = await conn.execute(
                "SELECT vibe FROM ratings WHERE chat_id = ? AND target_id = ? AND rater_id = ?",
                (GLOBAL, target_id, rater_id))
            row = await cur.fetchone()
            new = 0 if row is not None and row[0] == vibe else vibe
            await conn.execute(
                "INSERT INTO ratings (chat_id, target_id, rater_id, vibe, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (chat_id, target_id, rater_id) DO UPDATE SET vibe = excluded.vibe, "
                "updated_at = excluded.updated_at", (GLOBAL, target_id, rater_id, new or None, now()))
            return new

    async def set_score(self, chat_id: int, target_id: int, rater_id: int, score: int) -> None:
        await self.db.execute(
            "INSERT INTO ratings (chat_id, target_id, rater_id, score, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (chat_id, target_id, rater_id) DO UPDATE SET score = excluded.score, "
            "updated_at = excluded.updated_at", (GLOBAL, target_id, rater_id, score, now()))

    async def summary(self, chat_id: int, target_id: int) -> tuple[int, int, float | None, int]:
        """(جميل، سيئ، معدل الدرجة، عدد اللي أعطوا درجة)"""
        row = await self.db.fetchone(
            "SELECT COALESCE(SUM(vibe = 1), 0), COALESCE(SUM(vibe = -1), 0), AVG(score), COUNT(score) "
            "FROM ratings WHERE chat_id = ? AND target_id = ?", (GLOBAL, target_id))
        return int(row[0]), int(row[1]), (float(row[2]) if row[2] is not None else None), int(row[3])

    async def top(self, chat_id: int, min_votes: int = 3, limit: int = 10):
        return await self.db.fetchall(
            "SELECT r.target_id AS user_id, AVG(r.score) AS avg, COUNT(r.score) AS n, "
            "SUM(r.vibe = 1) AS good, u.first_name, u.last_name FROM ratings r "
            "LEFT JOIN users u ON u.user_id = r.target_id WHERE r.chat_id = ? AND r.score IS NOT NULL "
            "GROUP BY r.target_id HAVING COUNT(r.score) >= ? ORDER BY avg DESC, n DESC LIMIT ?",
            (GLOBAL, min_votes, limit))
