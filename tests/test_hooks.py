"""Tests for timetrace.hooks — HookManager and Notifier."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from timetrace.hooks import HookManager, Notifier


class TestHookManager:
    def test_creates_hooks_json(self, tmp_path):
        hm = HookManager(str(tmp_path))
        assert os.path.exists(hm.hooks_path)
        with open(hm.hooks_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "on_start" in data
        assert "on_stop" in data

    def test_trigger_no_raise_on_empty(self, tmp_path):
        hm = HookManager(str(tmp_path))
        # Should not raise even with no hooks configured
        hm.trigger("on_start", "test_task")

    def test_run_hooks_handles_corrupt_file(self, tmp_path):
        hm = HookManager(str(tmp_path))
        # Corrupt the file
        with open(hm.hooks_path, "w", encoding="utf-8") as f:
            f.write("{bad json!!")
        # Should not raise
        hm._run_hooks("on_start", "task", "")


class TestNotifier:
    def test_send_no_raise(self):
        # Should not raise on any platform
        Notifier.send("Test", "Hello")
