import os
from datetime import datetime, timedelta

import aiosqlite

from config import DB_PATH


class Database:
    """Асинхронная обертка над SQLite для задач и аналитики."""

    def __init__(self):
        self.db_path = DB_PATH

    async def init(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id        INTEGER PRIMARY KEY,
                    username       TEXT,
                    first_name     TEXT,
                    mood           TEXT DEFAULT 'normal',
                    registered_at  TEXT DEFAULT (datetime('now','localtime')),
                    last_active_at TEXT DEFAULT (datetime('now','localtime'))
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL,
                    title         TEXT NOT NULL,
                    category      TEXT DEFAULT 'Общее',
                    priority      INTEGER DEFAULT 2,
                    due_date      TEXT,
                    created_at    TEXT DEFAULT (datetime('now','localtime')),
                    completed_at  TEXT,
                    is_completed  INTEGER DEFAULT 0,
                    is_deleted    INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wins_journal (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    text       TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS slip_journal (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    reason     TEXT NOT NULL,
                    action     TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )
            await self._ensure_task_columns(conn)
            await conn.commit()

    async def _ensure_task_columns(self, conn: aiosqlite.Connection):
        cur = await conn.execute("PRAGMA table_info(tasks)")
        existing = {row[1] for row in await cur.fetchall()}
        if "category" not in existing:
            await conn.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'Общее'")
        if "priority" not in existing:
            await conn.execute("ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 2")
        if "due_date" not in existing:
            await conn.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
        cur = await conn.execute("PRAGMA table_info(users)")
        user_cols = {row[1] for row in await cur.fetchall()}
        if "mood" not in user_cols:
            await conn.execute("ALTER TABLE users ADD COLUMN mood TEXT DEFAULT 'normal'")

    @staticmethod
    def _normalize_priority(priority: int | None) -> int:
        if priority is None:
            return 2
        return max(1, min(3, int(priority)))

    async def add_user(self, user_id: int, username: str | None, first_name: str | None):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?,?,?)",
                (user_id, username, first_name),
            )
            await conn.commit()

    async def update_activity(self, user_id: int):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE users SET last_active_at = ? WHERE user_id = ?",
                (now, user_id),
            )
            await conn.commit()

    async def get_user(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def set_user_mood(self, user_id: int, mood: str):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE users SET mood = ? WHERE user_id = ?",
                (mood, user_id),
            )
            await conn.commit()

    async def get_user_mood(self, user_id: int) -> str:
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute("SELECT mood FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            if not row or not row[0]:
                return "normal"
            return row[0]

    async def get_all_users(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute("SELECT * FROM users")
            return [dict(r) for r in await cur.fetchall()]

    async def add_win_entry(self, user_id: int, text: str):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "INSERT INTO wins_journal (user_id, text) VALUES (?,?)",
                (user_id, text.strip()),
            )
            await conn.commit()

    async def get_recent_wins(self, user_id: int, limit: int = 7) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                """
                SELECT * FROM wins_journal
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def add_slip_entry(self, user_id: int, reason: str, action: str):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "INSERT INTO slip_journal (user_id, reason, action) VALUES (?,?,?)",
                (user_id, reason.strip(), action.strip()),
            )
            await conn.commit()

    async def get_recent_slips(self, user_id: int, limit: int = 5) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                """
                SELECT * FROM slip_journal
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def add_task(
        self,
        user_id: int,
        title: str,
        priority: int = 2,
        category: str = "Общее",
        due_date: str | None = None,
    ) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                """
                INSERT INTO tasks (user_id, title, priority, category, due_date, created_at)
                VALUES (?,?,?,?,?,?)
                """,
                (user_id, title, self._normalize_priority(priority), category.strip()[:30], due_date, now),
            )
            await conn.commit()
            return cur.lastrowid

    async def update_task(
        self,
        task_id: int,
        user_id: int,
        title: str | None = None,
        priority: int | None = None,
        category: str | None = None,
        due_date: str | None = None,
    ):
        fields = []
        values = []

        if title is not None:
            fields.append("title = ?")
            values.append(title.strip())
        if priority is not None:
            fields.append("priority = ?")
            values.append(self._normalize_priority(priority))
        if category is not None:
            fields.append("category = ?")
            values.append(category.strip()[:30] or "Общее")
        if due_date is not None:
            fields.append("due_date = ?")
            values.append(due_date)

        if not fields:
            return

        values.extend([task_id, user_id])
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                f"UPDATE tasks SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
                values,
            )
            await conn.commit()

    async def get_task(self, task_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_active_tasks(self, user_id: int) -> list[dict]:
        return await self.get_tasks_filtered(user_id, status="active")

    async def get_all_user_tasks(self, user_id: int) -> list[dict]:
        return await self.get_tasks_filtered(user_id, status="all")

    async def get_tasks_filtered(
        self,
        user_id: int,
        status: str = "all",
        search: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        where = ["user_id = ?", "is_deleted = 0"]
        params: list = [user_id]

        if status == "active":
            where.append("is_completed = 0")
        elif status == "done":
            where.append("is_completed = 1")

        if search:
            where.append("LOWER(title) LIKE ?")
            params.append(f"%{search.lower()}%")

        limit_sql = ""
        if limit:
            limit_sql = " LIMIT ?"
            params.append(limit)

        query = f"""
            SELECT * FROM tasks
            WHERE {' AND '.join(where)}
            ORDER BY
                is_completed ASC,
                priority ASC,
                CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END,
                due_date ASC,
                created_at DESC
            {limit_sql}
        """

        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(query, params)
            return [dict(r) for r in await cur.fetchall()]

    async def complete_task(self, task_id: int, user_id: int):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE tasks SET is_completed=1, completed_at=? WHERE id=? AND user_id=?",
                (now, task_id, user_id),
            )
            await conn.commit()

    async def reopen_task(self, task_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE tasks SET is_completed=0, completed_at=NULL WHERE id=? AND user_id=?",
                (task_id, user_id),
            )
            await conn.commit()

    async def delete_task(self, task_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE tasks SET is_deleted=1 WHERE id=? AND user_id=?",
                (task_id, user_id),
            )
            await conn.commit()

    async def get_completed_today(self, user_id: int) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                """
                SELECT COUNT(*) FROM tasks
                WHERE user_id=? AND is_completed=1 AND is_deleted=0
                AND DATE(completed_at)=?
                """,
                (user_id, today),
            )
            return (await cur.fetchone())[0]

    async def get_created_today(self, user_id: int) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                """
                SELECT COUNT(*) FROM tasks
                WHERE user_id=? AND is_deleted=0 AND DATE(created_at)=?
                """,
                (user_id, today),
            )
            return (await cur.fetchone())[0]

    async def get_due_today_count(self, user_id: int) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                """
                SELECT COUNT(*) FROM tasks
                WHERE user_id=? AND is_deleted=0 AND is_completed=0
                AND due_date = ?
                """,
                (user_id, today),
            )
            return (await cur.fetchone())[0]

    async def get_completion_dates(self, user_id: int, days: int = 365) -> list[str]:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                """
                SELECT DISTINCT DATE(completed_at) AS d FROM tasks
                WHERE user_id=? AND is_completed=1 AND is_deleted=0
                AND DATE(completed_at) >= ?
                ORDER BY d DESC
                """,
                (user_id, since),
            )
            return [r[0] for r in await cur.fetchall()]

    async def get_stats_period(self, user_id: int, days: int = 7) -> dict:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                """
                SELECT COUNT(*) FROM tasks
                WHERE user_id=? AND is_deleted=0 AND created_at >= ?
                """,
                (user_id, since),
            )
            created = (await cur.fetchone())[0]

            cur = await conn.execute(
                """
                SELECT COUNT(*) FROM tasks
                WHERE user_id=? AND is_completed=1 AND is_deleted=0
                AND completed_at >= ?
                """,
                (user_id, since),
            )
            completed = (await cur.fetchone())[0]

            cur = await conn.execute(
                """
                SELECT strftime('%w', completed_at) AS dow, COUNT(*) AS cnt
                FROM tasks
                WHERE user_id=? AND is_completed=1 AND is_deleted=0
                AND completed_at >= ?
                GROUP BY dow ORDER BY cnt DESC
                """,
                (user_id, since),
            )
            by_dow = await cur.fetchall()

        rate = round(completed / created * 100, 1) if created else 0.0
        return {
            "total_created": created,
            "total_completed": completed,
            "completion_rate": rate,
            "by_day_of_week": by_dow,
        }

    async def get_total_stats(self, user_id: int) -> dict:
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id=? AND is_deleted=0",
                (user_id,),
            )
            total = (await cur.fetchone())[0]

            cur = await conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id=? AND is_completed=1 AND is_deleted=0",
                (user_id,),
            )
            done = (await cur.fetchone())[0]

        return {
            "total": total,
            "completed": done,
            "pending": total - done,
            "completion_rate": round(done / total * 100, 1) if total else 0.0,
        }

    async def get_daily_completions(self, user_id: int, days: int = 7) -> list[tuple]:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                """
                SELECT DATE(completed_at) AS day, COUNT(*) AS cnt
                FROM tasks
                WHERE user_id=? AND is_completed=1 AND is_deleted=0
                AND DATE(completed_at) >= ?
                GROUP BY day ORDER BY day
                """,
                (user_id, since),
            )
            return await cur.fetchall()

    async def get_inactive_users(self, hours: int = 24) -> list[dict]:
        threshold = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                """
                SELECT u.* FROM users u
                WHERE u.last_active_at < ?
                AND EXISTS (
                    SELECT 1 FROM tasks t
                    WHERE t.user_id = u.user_id
                    AND t.is_completed = 0 AND t.is_deleted = 0
                )
                """,
                (threshold,),
            )
            return [dict(r) for r in await cur.fetchall()]


db = Database()
