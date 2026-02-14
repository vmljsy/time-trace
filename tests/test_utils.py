"""Tests for timetrace.utils — parse_tags and parse_time_input."""

from __future__ import annotations

from datetime import datetime

import pytest

from timetrace.config import TIME_FORMAT
from timetrace.utils import parse_tags, parse_time_input


# ── parse_tags ─────────────────────────────────────────────────────────

class TestParseTags:
    def test_single_tag(self):
        name, tags = parse_tags("coding #python")
        assert name == "coding"
        assert tags == ["python"]

    def test_multiple_tags(self):
        name, tags = parse_tags("review #frontend #urgent")
        assert name == "review"
        assert tags == ["frontend", "urgent"]

    def test_no_tags(self):
        name, tags = parse_tags("plain task")
        assert name == "plain task"
        assert tags == []

    def test_tags_lowered(self):
        name, tags = parse_tags("work #Python #GoLang")
        assert tags == ["python", "golang"]

    def test_tags_with_hyphens(self):
        name, tags = parse_tags("deploy #ci-cd #infra-ops")
        assert name == "deploy"
        assert tags == ["ci-cd", "infra-ops"]

    def test_empty_string(self):
        name, tags = parse_tags("")
        assert name == ""
        assert tags == []

    def test_tag_only_input(self):
        name, tags = parse_tags("#solo")
        assert name == ""
        assert tags == ["solo"]


# ── parse_time_input ───────────────────────────────────────────────────

class TestParseTimeInput:
    def test_full_datetime(self):
        result, err = parse_time_input("2026-02-15 14:30:00")
        assert err is None
        assert result == "2026-02-15 14:30:00"

    def test_datetime_no_seconds(self):
        result, err = parse_time_input("2026-02-15 14:30")
        assert err is None
        assert result == "2026-02-15 14:30:00"

    def test_time_only_with_seconds(self):
        result, err = parse_time_input("09:05:30")
        assert err is None
        dt = datetime.strptime(result, TIME_FORMAT)
        today = datetime.now()
        assert dt.year == today.year
        assert dt.month == today.month
        assert dt.day == today.day
        assert dt.hour == 9
        assert dt.minute == 5

    def test_time_only_hh_mm(self):
        result, err = parse_time_input("14:30")
        assert err is None
        dt = datetime.strptime(result, TIME_FORMAT)
        assert dt.hour == 14
        assert dt.minute == 30

    def test_empty_string_returns_none(self):
        result, err = parse_time_input("")
        assert result is None
        assert err is None

    def test_whitespace_only_returns_none(self):
        result, err = parse_time_input("   ")
        assert result is None
        assert err is None

    def test_invalid_input_returns_error(self):
        result, err = parse_time_input("not-a-time")
        assert result is None
        assert err is not None
        assert "Format" in err

    def test_partial_invalid_returns_error(self):
        result, err = parse_time_input("25:99")
        assert result is None
        assert err is not None
