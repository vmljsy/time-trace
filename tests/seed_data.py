"""
Seed script — populate the REAL TimeTrace database with sample entries
for the current week.  Run MANUALLY with:

    uv run python tests/seed_data.py

This file is excluded from pytest collection (no test_ prefix, plus
explicit exclusion in pyproject.toml).
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ╔══════════════════════════════════════════════════════════════════════╗
# ║                        CONFIGURATION                                ║
# ║  Edit the values below to customise what gets seeded.               ║
# ╚══════════════════════════════════════════════════════════════════════╝

# How many days back from today to seed (max = to Monday of this week)
SEED_DAYS: int = 30

# Min / max number of sessions created per day
SESSIONS_PER_DAY: tuple[int, int] = (2, 8)

# Earliest / latest hour a session can start
WORK_START_HOUR: int = 8
WORK_END_HOUR: int = 18

# Gap between sessions (minutes)
GAP_BETWEEN_SESSIONS: tuple[int, int] = (0, 60)

# Whether to clear ALL existing data before seeding
CLEAR_EXISTING: bool = True

# Projects: (task_name_with_tags, min_duration_min, max_duration_min)
PROJECTS: list[tuple[str, int, int]] = [
    ("Backend API #python #backend",        60, 180),
    ("Frontend UI #react #frontend",        45, 120),
    ("Code Review #review",                 20,  60),
    ("DevOps Pipeline #devops #ci-cd",      30,  90),
    ("Database Migration #sql #backend",    40, 100),
    ("Documentation #docs",                 15,  45),
    ("Sprint Planning #meeting",            30,  60),
    ("Bug Fixing #debug #hotfix",           20,  90),
    ("Unit Tests #testing #python",         30,  75),
    ("Design Sync #meeting #design",        25,  50),
    ("Meeting #meeting",                    30,  60),
    ("Deployment #deployment",                30,  60),
    ("Code Review #review",                 20,  60),
    ("Design Sync #meeting #design",        25,  50),
    ("Meeting 122 #meeting",                 30,  60),
]

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                     END OF CONFIGURATION                            ║
# ╚══════════════════════════════════════════════════════════════════════╝


from timetrace.database import TimeTrace


def generate_sessions() -> list[tuple[str, str, str]]:
    """Build a list of (task, start_str, end_str) for the seed period."""
    now = datetime.now()
    fmt = "%Y-%m-%d %H:%M:%S"

    # Go back SEED_DAYS but not before Monday of this week
    start_date = now - timedelta(days=SEED_DAYS - 1)
    sessions: list[tuple[str, str, str]] = []

    for d in range(SEED_DAYS):
        day = start_date + timedelta(days=d)
        hour = random.randint(WORK_START_HOUR, WORK_START_HOUR + 1)
        minute = 0

        count = random.randint(*SESSIONS_PER_DAY)
        daily_tasks = random.sample(PROJECTS, k=min(count, len(PROJECTS)))

        for task_str, min_dur, max_dur in daily_tasks:
            start = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            dur = random.randint(min_dur, max_dur)
            end = start + timedelta(minutes=dur)

            # Don't go past now or past WORK_END_HOUR
            if end.hour >= WORK_END_HOUR:
                end = end.replace(hour=WORK_END_HOUR, minute=0, second=0)
            if end > now:
                end = now - timedelta(minutes=1)
            if start >= end:
                continue

            sessions.append((task_str, start.strftime(fmt), end.strftime(fmt)))

            gap = random.randint(*GAP_BETWEEN_SESSIONS)
            next_start = end + timedelta(minutes=gap)
            hour = next_start.hour
            minute = next_start.minute

    return sessions


def main() -> None:
    app = TimeTrace()

    if CLEAR_EXISTING:
        import sqlite3
        print("🗑️  Clearing existing data...")
        with sqlite3.connect(app.db_path) as conn:
            conn.execute("DELETE FROM log_tags")
            conn.execute("DELETE FROM tags")
            conn.execute("DELETE FROM logs")
        app.refresh_cache()

    sessions = generate_sessions()
    print(f"🌱 Seeding {len(sessions)} sessions into: {app.db_path}")
    print(f"   Config: {SEED_DAYS} days, {SESSIONS_PER_DAY[0]}-{SESSIONS_PER_DAY[1]} sessions/day\n")

    for task, start, end in sessions:
        ok = app.add_manual_log(task, start, end)
        status = "✅" if ok else "❌"
        print(f"  {status}  {start} → {end}  {task}")

    print(f"\n🎉 Done! {len(sessions)} sessions added.")
    print("   Launch the TUI:  uv run python main.py")


if __name__ == "__main__":
    main()
