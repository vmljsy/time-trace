"""Tests for timetrace.console — Console buffer management."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from timetrace.console import Console


@pytest.fixture
def console():
    """Create a Console with a fixed 80×24 size."""
    with patch("shutil.get_terminal_size", return_value=(80, 24)):
        c = Console()
    return c


class TestConsole:
    def test_clear_buffer_fills_spaces(self, console):
        console.clear_buffer()
        assert len(console.buffer) == 24
        assert len(console.buffer[0]) == 80
        assert all(cell == " " for cell in console.buffer[0])

    def test_print_at_writes_text(self, console):
        console.print_at(0, 0, "Hi")
        # Cell should contain the character with reset escape
        assert "H" in console.buffer[0][0]
        assert "i" in console.buffer[0][1]

    def test_print_at_with_style(self, console):
        console.print_at(1, 5, "X", style="\033[1m")
        cell = console.buffer[1][5]
        assert "\033[1m" in cell
        assert "X" in cell

    def test_print_at_multiline(self, console):
        console.print_at(2, 0, "AB\nCD")
        assert "A" in console.buffer[2][0]
        assert "C" in console.buffer[3][0]

    def test_print_at_out_of_bounds_safe(self, console):
        # Should not raise
        console.print_at(100, 0, "offscreen")
        console.print_at(0, 200, "offscreen")
        console.print_at(-1, 0, "offscreen")

    def test_dimensions(self, console):
        assert console.width == 80
        assert console.height == 24
