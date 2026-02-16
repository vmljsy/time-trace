"""Tests for timetrace.database — TimeTrace core engine."""

from __future__ import annotations

import csv
import os
import sqlite3
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from timetrace.config import TIME_FORMAT


# ── Schema & Init ──────────────────────────────────────────────────────

class TestSchema:
    def test_tables_created(self, app):
        with sqlite3.connect(app.db_path) as conn:
            tables = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
        assert "logs" in tables
        assert "tags" in tables
        assert "log_tags" in tables

    def test_idempotent_init(self, app):
        # Running _init_db again should not raise
        app._init_db()


# ── Start / Stop ───────────────────────────────────────────────────────

class TestStartStop:
    def test_start_inserts_row(self, app):
        app.start("coding")
        active = app.get_active()
        assert active is not None
        assert active["action"] == "START"
        assert active["task"] == "coding"

    def test_start_auto_stops_previous(self, app):
        app.start("task_a")
        app.start("task_b")
        # After starting B, the active task should be B
        assert app.get_active()["task"] == "task_b"
        # History should contain task_a as a completed session
        history = app.get_recent_history()
        assert any(h["task"] == "task_a" for h in history)

    def test_stop_inserts_stop_row(self, app):
        app.start("work")
        app.stop()
        active = app.get_active()
        assert active["action"] == "STOP"

    def test_stop_noop_when_idle(self, app):
        # Should not raise  
        app.stop()
        app.stop()

    def test_start_empty_task_ignored(self, app):
        app.start("")
        app.start("   ")
        # No active task should be set
        assert app.get_active() is None or app.get_active()["action"] != "START"

    def test_start_with_tags(self, app):
        app.start("deploy #ci #prod")
        active = app.get_active()
        assert active["task"] == "deploy"
        tags = app.get_all_tags()
        assert "ci" in tags
        assert "prod" in tags


# ── Retroactive Start ─────────────────────────────────────────────────

class TestRetroactiveStart:
    def test_start_retroactive(self, app):
        app.start_retroactive("meeting", 30)
        active = app.get_active()
        assert active["task"] == "meeting"
        start_time = datetime.strptime(active["timestamp"], TIME_FORMAT)
        expected = datetime.now() - timedelta(minutes=30)
        # Allow 5-second tolerance
        assert abs((start_time - expected).total_seconds()) < 5


# ── Manual Logs ────────────────────────────────────────────────────────

class TestManualLog:
    def test_add_manual_log(self, app):
        ok = app.add_manual_log(
            "reading",
            "2026-02-15 10:00:00",
            "2026-02-15 11:00:00",
        )
        assert ok is True
        history = app.get_recent_history()
        assert any(h["task"] == "reading" for h in history)

    def test_invalid_timestamps_rejected(self, app):
        ok = app.add_manual_log("task", "not-a-date", "also-bad")
        assert ok is False

    def test_manual_log_with_tags(self, app):
        app.add_manual_log(
            "study #math #exam",
            "2026-02-15 08:00:00",
            "2026-02-15 09:00:00",
        )
        tags = app.get_all_tags()
        assert "math" in tags


# ── Delete Log ─────────────────────────────────────────────────────────

class TestDeleteLog:
    def test_delete_log(self, app):
        app.add_manual_log("temp", "2026-02-15 12:00:00", "2026-02-15 12:30:00")
        history = app.get_recent_history()
        if history:
            start_id = history[0]["start_id"]
            app.delete_log(start_id)
            app.refresh_cache()


# ── Edit Log ───────────────────────────────────────────────────────────

class TestEditLog:
    def test_edit_task_name(self, app):
        app.add_manual_log("old_name", "2026-02-15 14:00:00", "2026-02-15 15:00:00")
        history = app.get_recent_history()
        assert len(history) > 0
        entry = history[0]
        ok, err = app.edit_log(entry["start_id"], entry["stop_id"], new_task="new_name")
        assert ok is True
        assert err == ""
        app.refresh_cache()
        updated = app.get_recent_history()
        assert updated[0]["task"] == "new_name"

    def test_edit_timestamps(self, app):
        app.add_manual_log("timed", "2025-01-10 10:00:00", "2025-01-10 11:00:00")
        entry = app.get_recent_history()[0]
        ok, err = app.edit_log(
            entry["start_id"],
            entry["stop_id"],
            new_start="2025-01-10 09:00:00",
            new_end="2025-01-10 10:30:00",
        )
        assert ok is True

    def test_edit_start_after_end_rejected(self, app):
        app.add_manual_log("x", "2026-02-15 10:00:00", "2026-02-15 11:00:00")
        entry = app.get_recent_history()[0]
        ok, err = app.edit_log(
            entry["start_id"],
            entry["stop_id"],
            new_start="2026-02-15 12:00:00",
            new_end="2026-02-15 11:00:00",
        )
        assert ok is False
        assert "before" in err.lower() or "Start" in err

    def test_edit_exceeds_24h_rejected(self, app):
        app.add_manual_log("long", "2026-02-15 10:00:00", "2026-02-15 11:00:00")
        entry = app.get_recent_history()[0]
        ok, err = app.edit_log(
            entry["start_id"],
            entry["stop_id"],
            new_start="2026-02-01 00:00:00",
            new_end="2026-02-03 00:00:00",
        )
        assert ok is False
        assert "24" in err


# ── Stats ──────────────────────────────────────────────────────────────

class TestStats:
    def test_get_project_stats(self, app):
        app.add_manual_log("alpha", "2026-02-15 10:00:00", "2026-02-15 11:00:00")
        app.add_manual_log("beta", "2026-02-15 12:00:00", "2026-02-15 13:30:00")
        stats = app.get_project_stats(period="all")
        assert "alpha" in stats
        assert "beta" in stats
        assert stats["beta"] > stats["alpha"]

    def test_get_today_total(self, app):
        now = datetime.now()
        start = (now - timedelta(hours=1)).strftime(TIME_FORMAT)
        end = now.strftime(TIME_FORMAT)
        app.add_manual_log("today_work", start, end)
        total = app.get_today_total()
        assert ":" in total  # formatted as H:MM:SS

    def test_get_all_tags(self, app):
        app.add_manual_log("a #t1 #t2", "2026-02-15 10:00:00", "2026-02-15 11:00:00")
        tags = app.get_all_tags()
        assert "t1" in tags
        assert "t2" in tags

    def test_get_tag_stats(self, app):
        app.add_manual_log("x #dev", "2026-02-15 10:00:00", "2026-02-15 11:00:00")
        tag_stats = app.get_tag_stats(period="all")
        assert "dev" in tag_stats
        assert tag_stats["dev"] > 0


# ── Cache ──────────────────────────────────────────────────────────────

class TestCache:
    def test_refresh_populates_history(self, app):
        app.add_manual_log("cached", "2026-02-15 10:00:00", "2026-02-15 10:30:00")
        app.refresh_cache()
        assert len(app.get_recent_history()) > 0

    def test_get_projects(self, app):
        app.add_manual_log("proj_a", "2026-02-15 10:00:00", "2026-02-15 10:30:00")
        assert "proj_a" in app.get_projects()

    def test_history_limit(self, app):
        for i in range(5):
            start = f"2026-02-15 {10 + i}:00:00"
            end = f"2026-02-15 {10 + i}:30:00"
            app.add_manual_log(f"task_{i}", start, end)
        assert len(app.get_recent_history(limit=2)) == 2


# ── Heatmap ────────────────────────────────────────────────────────────

class TestHeatmap:
    def test_heatmap_returns_correct_shape(self, app):
        matrix = app.get_heatmap_matrix(days=3, start_h=8, end_h=12)
        # Should have up to 3 rows
        assert len(matrix) <= 3
        for label, vals in matrix:
            assert isinstance(label, str)
            # 8,9,10,11,12 → 5 columns
            assert len(vals) == 5

    def test_intensity_buckets(self, app):
        # Add a session in the current hour
        now = datetime.now()
        start = now.replace(minute=0, second=0).strftime(TIME_FORMAT)
        end = now.strftime(TIME_FORMAT)
        if start != end:
            app.add_manual_log("heatmap_task", start, end)
        matrix = app.get_heatmap_matrix(days=1, start_h=now.hour, end_h=now.hour)
        # Should have at least one row
        if matrix:
            vals = matrix[0][1]
            for v in vals:
                assert 0 <= v <= 4


# ── Timeline ──────────────────────────────────────────────────────────

class TestTimeline:
    def test_timeline_matrix_structure(self, app):
        app.add_manual_log("timeline_proj", "2026-02-15 09:00:00", "2026-02-15 10:00:00")
        matrix = app.get_timeline_matrix(days=7, start_h=8, end_h=20, period="all")
        for label, spans in matrix:
            assert isinstance(label, str)
            for proj, sf, ef in spans:
                assert isinstance(proj, str)
                assert sf < ef


# ── Export ─────────────────────────────────────────────────────────────

class TestExport:
    def test_export_csv(self, app):
        app.add_manual_log("exported", "2026-02-15 10:00:00", "2026-02-15 11:00:00")
        path = app.export_csv("test_export.csv")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert "ID" in header
            assert "Tags" in header

    def test_export_contains_data(self, app):
        app.add_manual_log("data #tag1", "2026-02-15 10:00:00", "2026-02-15 11:00:00")
        path = app.export_csv("test_data.csv")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "data" in content


# ── Backup ─────────────────────────────────────────────────────────────

class TestBackup:
    def test_backup_creates_file(self, app):
        path = app.backup_db()
        assert os.path.exists(path)
        assert "backups" in path
