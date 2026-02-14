"""Tests for timetrace.config — ConfigManager, themes, and constants."""

from __future__ import annotations

import json
import os

import pytest

from timetrace.config import (
    _CONFIG_DEFAULTS,
    PROJECT_COLORS,
    THEMES,
    TIME_FORMAT,
    ConfigManager,
)


# ── Constants ──────────────────────────────────────────────────────────

class TestConstants:
    def test_time_format(self):
        assert "%Y" in TIME_FORMAT
        assert "%H" in TIME_FORMAT
        assert "%M" in TIME_FORMAT
        assert "%S" in TIME_FORMAT

    def test_project_colors_has_enough(self):
        assert len(PROJECT_COLORS) >= 8


# ── Themes ─────────────────────────────────────────────────────────────

class TestThemes:
    REQUIRED_KEYS = {"box", "header", "highlight", "warn", "bar", "text", "dim",
                     "success", "error", "tag", "active"}

    def test_all_themes_have_required_keys(self):
        for name, theme in THEMES.items():
            missing = self.REQUIRED_KEYS - theme.keys()
            assert not missing, f"Theme '{name}' missing keys: {missing}"

    def test_default_theme_exists(self):
        assert "Default" in THEMES

    def test_heatmap_keys_present(self):
        heatmap_keys = {"heatmap_none", "heatmap_low", "heatmap_medium",
                        "heatmap_high", "heatmap_peak"}
        for name, theme in THEMES.items():
            missing = heatmap_keys - theme.keys()
            assert not missing, f"Theme '{name}' missing heatmap keys: {missing}"


# ── ConfigManager ──────────────────────────────────────────────────────

class TestConfigManager:
    def test_creates_hooks_json_if_missing(self, tmp_path):
        cm = ConfigManager(str(tmp_path))
        assert os.path.exists(cm.path)

    def test_get_returns_defaults(self, config_manager):
        cfg = config_manager.get()
        for key, default in _CONFIG_DEFAULTS.items():
            assert key in cfg, f"Default key '{key}' missing from config"

    def test_update_persists(self, config_manager):
        config_manager.update("theme", "Dark")
        cfg = config_manager.get()
        assert cfg["theme"] == "Dark"

    def test_update_and_re_read(self, config_manager):
        config_manager.update("idle_threshold", 999)
        fresh = ConfigManager(os.path.dirname(config_manager.path))
        assert fresh.get()["idle_threshold"] == 999

    def test_corrupt_json_falls_back(self, tmp_path):
        hooks_path = tmp_path / "hooks.json"
        hooks_path.write_text("{invalid json!!", encoding="utf-8")
        cm = ConfigManager(str(tmp_path))
        cfg = cm.get()
        # Should fall back to defaults
        assert cfg["theme"] == _CONFIG_DEFAULTS["theme"]

    def test_default_notifications_on(self, config_manager):
        assert config_manager.get()["notifications"] is True
