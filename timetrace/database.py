"""
Database — Core TimeTrace data layer.

All SQLite operations (CRUD for logs, tags, stats, heatmaps) live here.
The class keeps an in-memory cache that is refreshed after every write.
"""

from __future__ import annotations

import csv
import os
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any

from timetrace.config import ConfigManager, TIME_FORMAT
from timetrace.hooks import HookManager, Notifier
from timetrace.platform import Platform
from timetrace.utils import parse_tags


class TimeTrace:
    """Core application engine — wraps the SQLite database."""

    def __init__(self) -> None:
        self.dir: str = Platform.get_app_dir()
        self.db_path: str = os.path.join(self.dir, "timetrace.db")
        self.hooks = HookManager(self.dir)
        self.notifier = Notifier()
        self.config = ConfigManager(self.dir)
        self._init_db()

        # Cache
        self._cache_active: sqlite3.Row | None = None
        self._cache_active_tags: list[str] = []
        self._cache_projects: list[str] = []
        self._cache_history: list[dict[str, Any]] = []
        self._last_db_update: float = 0
        self.refresh_cache()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS logs "
                "(id INTEGER PRIMARY KEY, timestamp TEXT, action TEXT, task TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS tags "
                "(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS log_tags "
                "(log_id INTEGER REFERENCES logs(id) ON DELETE CASCADE, "
                " tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE, "
                " PRIMARY KEY (log_id, tag_id))"
            )

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------
    def backup_db(self) -> str:
        """Create a timestamped database backup.  Returns the backup path."""
        b_dir = os.path.join(self.dir, "backups")
        os.makedirs(b_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d")
        dest = os.path.join(b_dir, f"backup_{ts}.db")
        shutil.copy2(self.db_path, dest)
        return dest

    # ------------------------------------------------------------------
    # Tag helpers
    # ------------------------------------------------------------------
    def _ensure_tag(self, conn: sqlite3.Connection, name: str) -> int:
        """Insert-or-get a tag, return its id."""
        name = name.lower().strip()
        row = conn.execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()
        if row:
            return row[0]
        cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        return cur.lastrowid  # type: ignore[return-value]

    def _attach_tags(self, conn: sqlite3.Connection, log_id: int, tags: list[str]) -> None:
        """Link a log entry to tags via log_tags."""
        for t in tags:
            tag_id = self._ensure_tag(conn, t)
            conn.execute(
                "INSERT OR IGNORE INTO log_tags (log_id, tag_id) VALUES (?, ?)",
                (log_id, tag_id),
            )

    def _get_tags_for_log(self, conn: sqlite3.Connection, log_id: int) -> list[str]:
        """Return list of tag names for a log entry."""
        rows = conn.execute(
            "SELECT t.name FROM tags t JOIN log_tags lt ON t.id=lt.tag_id WHERE lt.log_id=?",
            (log_id,),
        ).fetchall()
        return [r[0] for r in rows]

    def get_all_tags(self) -> list[str]:
        """Return all known tag names."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT name FROM tags ORDER BY name").fetchall()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Shared time-calculation helper
    # ------------------------------------------------------------------
    def _iter_sessions(
        self, rows: list[sqlite3.Row]
    ) -> list[tuple[sqlite3.Row, sqlite3.Row, float]]:
        """Yield ``(start_row, stop_row, seconds)`` for consecutive START/STOP pairs."""
        sessions: list[tuple[sqlite3.Row, sqlite3.Row, float]] = []
        for i in range(len(rows) - 1):
            if rows[i]["action"] == "START" and rows[i + 1]["action"] == "STOP":
                t1 = datetime.strptime(rows[i]["timestamp"], TIME_FORMAT)
                t2 = datetime.strptime(rows[i + 1]["timestamp"], TIME_FORMAT)
                sessions.append((rows[i], rows[i + 1], (t2 - t1).total_seconds()))
        return sessions

    def _active_seconds(self) -> float:
        """Seconds elapsed since the current active task started (0 if idle)."""
        if self._cache_active and self._cache_active["action"] == "START":
            t1 = datetime.strptime(self._cache_active["timestamp"], TIME_FORMAT)
            return (datetime.now() - t1).total_seconds()
        return 0.0

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_tag_stats(self, period: str = "all") -> dict[str, float]:
        """Return ``{tag: seconds}`` for the specified *period*."""
        timestamp_filter = self._period_start(period)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM logs WHERE timestamp >= ? ORDER BY id ASC",
                (timestamp_filter,),
            ).fetchall()

            stats: dict[str, float] = {}
            for start_row, _stop_row, secs in self._iter_sessions(rows):
                for tag in self._get_tags_for_log(conn, start_row["id"]):
                    stats[tag] = stats.get(tag, 0) + secs

            # Add active time
            if self._cache_active and self._cache_active["action"] == "START":
                t1 = datetime.strptime(self._cache_active["timestamp"], TIME_FORMAT)
                start_date = self._parse_period_date(period)
                if not start_date or t1 >= start_date:
                    active_secs = self._active_seconds()
                    for tag in self._get_tags_for_log(conn, self._cache_active["id"]):
                        stats[tag] = stats.get(tag, 0) + active_secs

        return dict(sorted(stats.items(), key=lambda kv: kv[1], reverse=True)[:8])

    def get_project_stats(self, period: str = "all") -> dict[str, float]:
        """Return ``{project: seconds}`` for the specified *period*."""
        timestamp_filter = self._period_start(period)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM logs WHERE timestamp >= ? ORDER BY id ASC",
                (timestamp_filter,),
            ).fetchall()

        stats: dict[str, float] = {}
        for start_row, _stop_row, secs in self._iter_sessions(rows):
            p = start_row["task"]
            stats[p] = stats.get(p, 0) + secs

        # Add active time
        if self._cache_active and self._cache_active["action"] == "START":
            t1 = datetime.strptime(self._cache_active["timestamp"], TIME_FORMAT)
            start_date = self._parse_period_date(period)
            if not start_date or t1 >= start_date:
                p = self._cache_active["task"]
                stats[p] = stats.get(p, 0) + self._active_seconds()

        return dict(sorted(stats.items(), key=lambda kv: kv[1], reverse=True)[:8])

    def get_today_total(self) -> str:
        """Total tracked time today as ``H:MM:SS``."""
        start_of_day = datetime.now().strftime("%Y-%m-%d 00:00:00")
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM logs WHERE timestamp >= ? ORDER BY id ASC",
                (start_of_day,),
            ).fetchall()

        total_sec = sum(secs for _, _, secs in self._iter_sessions(rows))

        # Add current active session
        if self._cache_active and self._cache_active["action"] == "START":
            t1 = datetime.strptime(self._cache_active["timestamp"], TIME_FORMAT)
            if t1 >= datetime.strptime(start_of_day, TIME_FORMAT):
                total_sec += self._active_seconds()

        return str(timedelta(seconds=int(total_sec)))

    # ------------------------------------------------------------------
    # Period helpers
    # ------------------------------------------------------------------
    def _parse_period_date(self, period: str) -> datetime | None:
        now = datetime.now()
        if period == "today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "week":
            return (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        if period == "month":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return None

    def _period_start(self, period: str) -> str:
        dt = self._parse_period_date(period)
        return dt.strftime(TIME_FORMAT) if dt else "1970-01-01 00:00:00"

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------
    def refresh_cache(self) -> None:
        """Reload in-memory caches from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            self._cache_active = conn.execute(
                "SELECT * FROM logs ORDER BY id DESC LIMIT 1"
            ).fetchone()

            self._cache_active_tags = []
            if self._cache_active:
                self._cache_active_tags = self._get_tags_for_log(conn, self._cache_active["id"])

            rows = conn.execute(
                "SELECT DISTINCT task FROM logs ORDER BY id DESC LIMIT 10"
            ).fetchall()
            self._cache_projects = [r[0] for r in rows]

            rows = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 100").fetchall()

            history: list[dict[str, Any]] = []
            for i in range(len(rows) - 1):
                if rows[i]["action"] == "STOP" and rows[i + 1]["action"] == "START":
                    end = datetime.strptime(rows[i]["timestamp"], TIME_FORMAT)
                    start = datetime.strptime(rows[i + 1]["timestamp"], TIME_FORMAT)
                    tags = self._get_tags_for_log(conn, rows[i + 1]["id"])
                    history.append(
                        {
                            "task": rows[i]["task"],
                            "duration": str(end - start).split(".")[0],
                            "start_id": rows[i + 1]["id"],
                            "stop_id": rows[i]["id"],
                            "start_time": rows[i + 1]["timestamp"],
                            "stop_time": rows[i]["timestamp"],
                            "tags": tags,
                        }
                    )

        self._cache_history = history
        self._last_db_update = time.time()

    # Convenience accessors
    def get_active(self) -> sqlite3.Row | None:
        return self._cache_active

    def get_projects(self) -> list[str]:
        return self._cache_projects

    def get_recent_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._cache_history[:limit]

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------
    def start(self, task: str) -> None:
        """Start tracking a task (stops any active task first)."""
        if not task.strip():
            return
        clean_name, tags = parse_tags(task)
        if not clean_name:
            clean_name = task.strip()
        self.stop()
        self.backup_db()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.execute(
                "INSERT INTO logs (timestamp, action, task) VALUES (?, ?, ?)",
                (datetime.now().strftime(TIME_FORMAT), "START", clean_name),
            )
            if tags:
                self._attach_tags(conn, cur.lastrowid, tags)  # type: ignore[arg-type]
        self.hooks.trigger("on_start", clean_name)
        tags_str = " ".join(f"#{t}" for t in tags) if tags else ""
        cfg = self.config.get()
        if cfg.get("notifications", True):
            self.notifier.send("▶️ Task Started", f"{clean_name} {tags_str}".strip())
        self.refresh_cache()

    def start_retroactive(self, task: str, minutes_ago: int) -> None:
        """Start a task backdated by *minutes_ago* minutes."""
        if not task.strip():
            return
        clean_name, tags = parse_tags(task)
        if not clean_name:
            clean_name = task.strip()
        self.stop()
        self.backup_db()
        start_time = datetime.now() - timedelta(minutes=int(minutes_ago))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.execute(
                "INSERT INTO logs (timestamp, action, task) VALUES (?, ?, ?)",
                (start_time.strftime(TIME_FORMAT), "START", clean_name),
            )
            if tags:
                self._attach_tags(conn, cur.lastrowid, tags)  # type: ignore[arg-type]
        self.refresh_cache()

    def stop(self) -> None:
        """Stop the active task (no-op if nothing is running)."""
        active = self.get_active()
        if not active or active["action"] != "START":
            return
        now = datetime.now()
        start_t = datetime.strptime(active["timestamp"], TIME_FORMAT)
        dur = str(now - start_t).split(".")[0]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.execute(
                "INSERT INTO logs (timestamp, action, task) VALUES (?, ?, ?)",
                (now.strftime(TIME_FORMAT), "STOP", active["task"]),
            )
            # Copy tags from START to STOP entry
            start_tags = self._get_tags_for_log(conn, active["id"])
            if start_tags:
                self._attach_tags(conn, cur.lastrowid, start_tags)  # type: ignore[arg-type]

            tags_str = " ".join(f"#{t}" for t in start_tags) if start_tags else ""

        self.hooks.trigger("on_stop", active["task"], dur)
        cfg = self.config.get()
        if cfg.get("notifications", True):
            self.notifier.send(
                "⏹️ Task Stopped",
                f"{active['task']} {tags_str}\nDuration: {dur}".strip(),
            )
        self.refresh_cache()

    def add_manual_log(self, task: str, start_str: str, end_str: str) -> bool:
        """Insert a completed session manually.  Returns ``True`` on success."""
        try:
            datetime.strptime(start_str, TIME_FORMAT)
            datetime.strptime(end_str, TIME_FORMAT)
        except ValueError:
            return False

        clean_name, tags = parse_tags(task)
        if not clean_name:
            clean_name = task.strip()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cur1 = conn.execute(
                "INSERT INTO logs (timestamp, action, task) VALUES (?, ?, ?)",
                (start_str, "START", clean_name),
            )
            cur2 = conn.execute(
                "INSERT INTO logs (timestamp, action, task) VALUES (?, ?, ?)",
                (end_str, "STOP", clean_name),
            )
            if tags:
                self._attach_tags(conn, cur1.lastrowid, tags)  # type: ignore[arg-type]
                self._attach_tags(conn, cur2.lastrowid, tags)  # type: ignore[arg-type]
        self.refresh_cache()
        return True

    def delete_log(self, log_id: int) -> None:
        """Delete a single log row by id."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM logs WHERE id=?", (log_id,))
        self.refresh_cache()

    def edit_log(
        self,
        start_id: int,
        stop_id: int,
        new_task: str | None = None,
        new_start: str | None = None,
        new_end: str | None = None,
    ) -> tuple[bool, str]:
        """Edit a log entry pair.  Returns ``(success, error_message)``."""
        # Validate timestamps
        if new_start:
            try:
                s = datetime.strptime(new_start, TIME_FORMAT)
            except ValueError:
                return False, "Invalid start format (YYYY-MM-DD HH:MM:SS)"
            if s > datetime.now():
                return False, "Start time cannot be in the future"
        if new_end:
            try:
                e = datetime.strptime(new_end, TIME_FORMAT)
            except ValueError:
                return False, "Invalid end format (YYYY-MM-DD HH:MM:SS)"
            if e > datetime.now():
                return False, "End time cannot be in the future"
        if new_start and new_end:
            s = datetime.strptime(new_start, TIME_FORMAT)
            e = datetime.strptime(new_end, TIME_FORMAT)
            if s >= e:
                return False, "Start must be before End"
            if (e - s).total_seconds() > 86400:
                return False, "Session cannot exceed 24 hours"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            if new_task:
                clean_name, tags = parse_tags(new_task)
                if not clean_name:
                    clean_name = new_task.strip()
                conn.execute("UPDATE logs SET task=? WHERE id=?", (clean_name, start_id))
                conn.execute("UPDATE logs SET task=? WHERE id=?", (clean_name, stop_id))
                conn.execute("DELETE FROM log_tags WHERE log_id=?", (start_id,))
                conn.execute("DELETE FROM log_tags WHERE log_id=?", (stop_id,))
                if tags:
                    self._attach_tags(conn, start_id, tags)
                    self._attach_tags(conn, stop_id, tags)
            if new_start:
                conn.execute("UPDATE logs SET timestamp=? WHERE id=?", (new_start, start_id))
            if new_end:
                conn.execute("UPDATE logs SET timestamp=? WHERE id=?", (new_end, stop_id))
        self.refresh_cache()
        return True, ""

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export_csv(self, filename: str = "timetrace_export.csv") -> str:
        """Export all logs to CSV.  Returns the file path."""
        path = os.path.join(self.dir, filename)
        with sqlite3.connect(self.db_path) as conn, open(
            path, "w", newline="", encoding="utf-8"
        ) as fh:
            writer = csv.writer(fh)
            writer.writerow(["ID", "Timestamp", "Action", "Task", "Tags"])
            for row in conn.execute("SELECT * FROM logs"):
                tags = self._get_tags_for_log(conn, row[0])
                writer.writerow(list(row) + [",".join(tags)])
        return path

    # ------------------------------------------------------------------
    # Config convenience (delegate to ConfigManager)
    # ------------------------------------------------------------------
    def get_config_path(self) -> str:
        return self.config.path

    def get_config(self) -> dict[str, Any]:
        return self.config.get()

    def update_config(self, key: str, value: Any) -> None:
        self.config.update(key, value)

    # ------------------------------------------------------------------
    # Heatmap
    # ------------------------------------------------------------------
    def get_heatmap_matrix(
        self,
        days: int = 7,
        start_h: int = 8,
        end_h: int = 20,
        weekdays: str = "MTWTFSS",
    ) -> list[tuple[str, list[int]]]:
        """Build a heatmap matrix for the activity view.

        Returns ``[(day_label, [intensity_0_to_4, ...])]``.
        """
        now = datetime.now()
        query_date = (now - timedelta(days=days + 1)).replace(
            hour=0, minute=0, second=0
        ).strftime(TIME_FORMAT)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM logs WHERE timestamp >= ? ORDER BY id ASC",
                (query_date,),
            ).fetchall()

        # Bucket seconds into "YYYY-MM-DD HH" keys
        buckets: dict[str, float] = {}

        def _bucket_session(t1: datetime, t2: datetime) -> None:
            current = t1
            while current < t2:
                hour_end = current.replace(minute=0, second=0) + timedelta(hours=1)
                end_point = min(hour_end, t2)
                k = current.strftime("%Y-%m-%d %H")
                buckets[k] = buckets.get(k, 0) + (end_point - current).total_seconds()
                current = hour_end

        for start_row, _stop_row, _secs in self._iter_sessions(rows):
            t1 = datetime.strptime(start_row["timestamp"], TIME_FORMAT)
            t2 = datetime.strptime(_stop_row["timestamp"], TIME_FORMAT)
            _bucket_session(t1, t2)

        # Active task
        active = self.get_active()
        if active and active["action"] == "START":
            t1 = datetime.strptime(active["timestamp"], TIME_FORMAT)
            _bucket_session(t1, datetime.now())

        # Build matrix — most recent day first
        matrix: list[tuple[str, list[int]]] = []
        for d in range(days):
            curr_date = now - timedelta(days=d)
            wd = curr_date.weekday()
            if wd < len(weekdays) and weekdays[wd] == "-":
                continue

            date_str = curr_date.strftime("%Y-%m-%d")
            if d == 0:
                label = "Tod"
            elif d == 1:
                label = "Ydy"
            else:
                label = curr_date.strftime("%a")

            row_vals: list[int] = []
            for h in range(start_h, end_h + 1):
                sec = buckets.get(f"{date_str} {h:02d}", 0)
                if sec < 60:
                    val = 0
                elif sec < 900:
                    val = 1
                elif sec < 1800:
                    val = 2
                elif sec < 2700:
                    val = 3
                else:
                    val = 4
                row_vals.append(val)

            matrix.append((label, row_vals))

        return matrix
