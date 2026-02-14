"""Tests for timetrace.formatter — TableFormatter and wrapper functions."""

from __future__ import annotations

import pytest

from timetrace.formatter import (
    Column,
    TableFormatter,
    format_config_list,
    format_history_table,
    format_report_bars,
)


# ── TableFormatter ─────────────────────────────────────────────────────

class TestTableFormatter:
    def test_basic_formatting(self):
        cols = [Column("name", "Name", 10), Column("val", "Value", 5)]
        tf = TableFormatter(cols, sep=" | ")
        rows = tf.format_batch([{"name": "alpha", "val": "42"}])
        assert len(rows) == 1
        assert "alpha" in rows[0][0]
        assert "42" in rows[0][0]

    def test_right_alignment(self):
        cols = [Column("n", "N", 6, ">")]
        tf = TableFormatter(cols)
        rows = tf.format_batch([{"n": "hi"}])
        line = rows[0][0]
        assert line.endswith("hi") or line.strip() == "hi"

    def test_header_generation(self):
        cols = [Column("x", "Header", 10)]
        tf = TableFormatter(cols, show_header=True)
        rows = tf.format_batch([{"x": "data"}])
        assert len(rows) == 2  # header + 1 data row
        assert "Header" in rows[0][0]

    def test_custom_formatter(self):
        def double(val, entry):
            return f"${val}"

        cols = [Column("price", "Price", 8, formatter=double)]
        tf = TableFormatter(cols)
        rows = tf.format_batch([{"price": "100"}])
        assert "$100" in rows[0][0]

    def test_row_style_provider(self):
        cols = [Column("a", "A", 5)]
        tf = TableFormatter(cols)

        def styler(i, entry):
            return "BOLD" if i == 0 else ""

        rows = tf.format_batch([{"a": "x"}, {"a": "y"}], row_style_provider=styler)
        assert rows[0][1] == "BOLD"
        assert rows[1][1] == ""

    def test_truncation(self):
        cols = [Column("txt", "T", 3)]
        tf = TableFormatter(cols)
        rows = tf.format_batch([{"txt": "abcdef"}])
        # Value should be truncated to width 3
        assert "abc" in rows[0][0]
        assert "def" not in rows[0][0]


# ── format_report_bars ─────────────────────────────────────────────────

class TestFormatReportBars:
    def test_empty_stats(self):
        assert format_report_bars({}, 20) == []

    def test_single_project(self):
        result = format_report_bars({"coding": 3600}, 20)
        assert len(result) == 2  # TOTAL + 1 project
        assert result[0][0] == "TOTAL"

    def test_multiple_projects(self):
        result = format_report_bars({"A": 1000, "B": 2000}, 20)
        assert len(result) == 3  # TOTAL + 2 projects

    def test_tag_mode_prefix(self):
        result = format_report_bars({"python": 3600}, 20, mode="tag")
        assert result[1][0].startswith("#")


# ── format_config_list ─────────────────────────────────────────────────

class TestFormatConfigList:
    def test_category_headers(self):
        options = [
            ("General", "theme", "Theme", "cycle", ["Default", "Dark"]),
            ("General", "notifications", "Notifications", "bool", None),
        ]
        cfg = {"theme": "Default", "notifications": True}
        rows = format_config_list(options, cfg)
        # First row should be a category header
        assert "[General]" in rows[0][0]
        assert rows[0][2] is True  # is_category flag

    def test_bool_on_off(self):
        options = [("Cat", "flag", "My Flag", "bool", None)]
        rows_on = format_config_list(options, {"flag": True})
        rows_off = format_config_list(options, {"flag": False})
        # data row is at index 1 (after category header)
        assert "ON" in rows_on[1][0]
        assert "OFF" in rows_off[1][0]

    def test_cycle_value_shown(self):
        options = [("Cat", "theme", "Theme", "cycle", ["A", "B"])]
        rows = format_config_list(options, {"theme": "B"})
        assert "B" in rows[1][0]
