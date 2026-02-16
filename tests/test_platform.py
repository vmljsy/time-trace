"""Tests for timetrace.platform — Platform OS helpers."""

from __future__ import annotations

import os

import pytest

from timetrace.platform import Platform


class TestPlatform:
    def test_get_app_dir_exists(self):
        path = Platform.get_app_dir()
        assert os.path.isdir(path)

    def test_get_idle_seconds_non_negative(self):
        seconds = Platform.get_idle_seconds()
        assert isinstance(seconds, float)
        assert seconds >= 0.0
