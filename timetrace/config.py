"""
Config — Application configuration, theme definitions, and constants.
"""

from __future__ import annotations

import json
import os
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

THEMES: dict[str, dict[str, str]] = {
    "Default": {
        "box": "\033[0m",
        "header": "\033[1;36m",
        "highlight": "\033[1;32m",
        "warn": "\033[5;33m",
        "bar": "\033[36m",
    },
    "Dark": {
        "box": "\033[90m",
        "header": "\033[94m",
        "highlight": "\033[92m",
        "warn": "\033[91m",
        "bar": "\033[94m",
    },
    "Retro": {
        "box": "\033[32m",
        "header": "\033[32m",
        "highlight": "\033[1;32m",
        "warn": "\033[32m",
        "bar": "\033[32m",
    },
}

_CONFIG_DEFAULTS: dict[str, Any] = {
    "idle_threshold": 300,
    "auto_backup": True,
    "backup_freq": "STOP",
    "feature_billing": False,
    "feature_html_report": False,
    "theme": "Default",
    "heatmap_days": 7,
    "heatmap_start": 6,
    "heatmap_end": 23,
    "heatmap_weekdays": "MTWTFSS",
    "notifications": True,
    "on_start": [],
    "on_stop": [],
}


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------
class ConfigManager:
    """Read / write the JSON configuration file (``hooks.json``)."""

    def __init__(self, app_dir: str) -> None:
        self.path: str = os.path.join(app_dir, "hooks.json")
        # Ensure the file exists with at least an empty object
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump({"on_start": [], "on_stop": []}, fh, indent=4)

    def get(self) -> dict[str, Any]:
        """Return merged defaults + saved config."""
        cfg = dict(_CONFIG_DEFAULTS)
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    saved = json.load(fh)
                cfg.update(saved)
            except (json.JSONDecodeError, OSError):
                pass  # fall back to defaults
        return cfg

    def update(self, key: str, value: Any) -> None:
        """Persist a single config key."""
        cfg = self.get()
        cfg[key] = value
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=4)
