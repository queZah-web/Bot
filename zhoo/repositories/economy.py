"""المحفظة: كل تغيير بالرصيد ذري وينسجل، والرصيد ما يصير سالب أبداً."""
from __future__ import annotations

from zhoo.database.db import Database, now


class InsufficientFunds(Exception):
    pass


class EconomyRepo:
    def __init__(self, db: Database):
        self.db = db

    async def wallet(self, chat_id: int, user_id: int):
        row = await self.db.fetchone("SELECT * FROM wallets WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        if row is not None:
            return row
        return {"balance": 0, "total_earned": 0, "streak": 0, "last_daily": None,
                "title_item": None, "frame_item": None, "custom_title": None}

    async def _change(self, conn, chat_id: int, user_id: int, amount: int, kind: str, ref: str | None) -> int:
        cur = await conn.execute("SELECT balance FROM wallets WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        row = await cur.fetchone()
        balance = row[0] if row else 0
        new = balance + amount
        if new < 0:
            raise InsufficientFunds(balance)
        earned = amount if amount > 0 and kind not in ("transfer_in", "admin_give", "withdraw", "rob_in") else 0
        await conn.execute(
            "INSERT INTO wallets (chat_id, user_id, balance, total_earned) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET balance = ?, total_earned = total_earned + ?",
            (chat_id, user_id, new, earned, new, earned))
        await conn.execute(
            "INSERT INTO transactions (chat_id, user_id, amount, kind, ref, balance_after, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", (chat_id, user_id, amount, kind, ref, new, now()))
        return new

    async def change_in(self, conn, chat_id: int, user_id: int, amount: int, kind: str, ref: str | None = None) -> int:
        """نفس change بس داخل معاملة مفتوحة (للبنك: إيداع، سحب، زرف)."""
        return await self._change(conn, chat_id, user_id, amount, kind, ref)

    async def change(self, chat_id: int, user_id: int, amount: int, kind: str, ref: str | None = None) -> int:
        """يضيف (موجب) أو يخصم (سالب). يرفع InsufficientFunds إذا الرصيد ما يكفي."""
        async with self.db.transaction() as conn:
            return await self._change(conn, chat_id, user_id, amount, kind, ref)

    async def transfer(self, chat_id: int, from_id: int, to_id: int, amount: int, fee: int) -> tuple[int, int]:
        """تحويل بمعاملة وحدة: يا ينجح كله يا ما يصير شي."""
        async with self.db.transaction() as conn:
            a = await self._change(conn, chat_id, from_id, -(amount + fee), "transfer_out", str(to_id))
            b = await self._change(conn, chat_id, to_id, amount, "transfer_in", str(from_id))
            return a, b

    async def buy(self, chat_id: int, user_id: int, item: str, price: int, slot: str,
                  custom_text: str | None = None) -> int:
        """يشتري ويلبس بنفس المعاملة."""
        async with self.db.transaction() as conn:
            new = await self._change(conn, chat_id, user_id, -price, "buy", item)
            await conn.execute("INSERT OR IGNORE INTO inventory (chat_id, user_id, item, created_at) VALUES (?, ?, ?, ?)",
                               (chat_id, user_id, item, now()))
            await conn.execute(f"UPDATE wallets SET {slot} = ? WHERE chat_id = ? AND user_id = ?",
                               (custom_text if slot == "custom_title" else item, chat_id, user_id))
            if slot == "custom_title":
                await conn.execute("UPDATE wallets SET title_item = ? WHERE chat_id = ? AND user_id = ?",
                                   (item, chat_id, user_id))
            return new

    async def owned(self, chat_id: int, user_id: int) -> set[str]:
        rows = await self.db.fetchall("SELECT item FROM inventory WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        return {r["item"] for r in rows}

    async def equip(self, chat_id: int, user_id: int, slot: str, item: str | None) -> None:
        assert slot in ("title_item", "frame_item")
        await self.db.execute(f"UPDATE wallets SET {slot} = ? WHERE chat_id = ? AND user_id = ?", (item, chat_id, user_id))

    async def set_daily(self, chat_id: int, user_id: int, streak: int, ts: int) -> None:
        await self.db.execute("UPDATE wallets SET streak = ?, last_daily = ? WHERE chat_id = ? AND user_id = ?",
                              (streak, ts, chat_id, user_id))

    async def sent_since(self, chat_id: int, user_id: int, seconds: int) -> int:
        return -await self.db.fetchval(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE chat_id = ? AND user_id = ? "
            "AND kind = 'transfer_out' AND created_at > ?", (chat_id, user_id, now() - seconds), default=0)

    async def history(self, chat_id: int, user_id: int, limit: int = 10):
        return await self.db.fetchall(
            "SELECT * FROM transactions WHERE chat_id = ? AND user_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, user_id, limit))

    async def richest(self, chat_id: int, limit: int = 10):
        return await self.db.fetchall(
            "SELECT w.user_id, w.balance + COALESCE(b.balance, 0) AS value, u.first_name, u.last_name FROM wallets w "
            "LEFT JOIN bank_accounts b ON b.chat_id = w.chat_id AND b.user_id = w.user_id "
            "LEFT JOIN users u ON u.user_id = w.user_id WHERE w.chat_id = ? AND w.balance + COALESCE(b.balance, 0) > 0 "
            "ORDER BY value DESC LIMIT ?", (chat_id, limit))

    # ── المهام اليومية ──
    async def mission_progress(self, chat_id: int, user_id: int, day: str, key: str, step: int,
                               target: int) -> bool:
        """يزيد التقدم. يرجع True مرة وحدة بس لما تكتمل المهمة."""
        async with self.db.transaction() as conn:
            await conn.execute(
                "INSERT INTO missions (chat_id, user_id, day, key, progress) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (chat_id, user_id, day, key) DO UPDATE SET progress = progress + excluded.progress "
                "WHERE missions.done = 0", (chat_id, user_id, day, key, step))
            cur = await conn.execute(
                "SELECT progress, done FROM missions WHERE chat_id = ? AND user_id = ? AND day = ? AND key = ?",
                (chat_id, user_id, day, key))
            progress, done = await cur.fetchone()
            if not done and progress >= target:
                await conn.execute(
                    "UPDATE missions SET done = 1 WHERE chat_id = ? AND user_id = ? AND day = ? AND key = ?",
                    (chat_id, user_id, day, key))
                return True
            return False

    async def missions_of(self, chat_id: int, user_id: int, day: str) -> dict[str, tuple[int, bool]]:
        rows = await self.db.fetchall(
            "SELECT key, progress, done FROM missions WHERE chat_id = ? AND user_id = ? AND day = ?",
            (chat_id, user_id, day))
        return {r["key"]: (r["progress"], bool(r["done"])) for r in rows}

    async def prune_missions(self, before_day: str) -> int:
        return await self.db.execute("DELETE FROM missions WHERE day < ?", (before_day,))
