"""
Shared pytest fixtures for TimeTrace test suite.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_app_dir(tmp_path):
    """Provide a temporary application directory with a default hooks.json."""
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text(json.dumps({"on_start": [], "on_stop": []}, indent=4), encoding="utf-8")
    return tmp_path


@pytest.fixture
def app(tmp_app_dir):
    """Return a TimeTrace instance fully isolated to a temp directory."""
    with patch("timetrace.platform.Platform.get_app_dir", return_value=str(tmp_app_dir)):
        from timetrace.database import TimeTrace
        instance = TimeTrace()
    return instance


@pytest.fixture
def config_manager(tmp_app_dir):
    """Return an isolated ConfigManager."""
    from timetrace.config import ConfigManager
    return ConfigManager(str(tmp_app_dir))
