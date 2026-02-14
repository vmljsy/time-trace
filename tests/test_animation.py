"""Tests for timetrace.animation — spinners and registry."""

from __future__ import annotations

import pytest

from timetrace.animation import (
    BouncingSpinner,
    FrameSpinner,
    SPINNERS,
    get_spinner,
)


# ── FrameSpinner ───────────────────────────────────────────────────────

class TestFrameSpinner:
    def test_cycles_through_frames(self):
        sp = FrameSpinner(["A", "B", "C"])
        assert sp.next_frame() == "A"
        assert sp.next_frame() == "B"
        assert sp.next_frame() == "C"

    def test_wraps_around(self):
        sp = FrameSpinner(["X", "Y"])
        sp.next_frame()  # X
        sp.next_frame()  # Y
        assert sp.next_frame() == "X"

    def test_reset(self):
        sp = FrameSpinner(["A", "B", "C"])
        sp.next_frame()
        sp.next_frame()
        sp.reset()
        assert sp.next_frame() == "A"

    def test_single_frame(self):
        sp = FrameSpinner(["O"])
        assert sp.next_frame() == "O"
        assert sp.next_frame() == "O"


# ── BouncingSpinner ────────────────────────────────────────────────────

class TestBouncingSpinner:
    def test_bounces_forward_and_back(self):
        sp = BouncingSpinner(["1", "2", "3"])
        frames = [sp.next_frame() for _ in range(6)]
        # Should go 1,2,3,2,1,2 (ping-pong)
        assert frames[0] == "1"
        assert frames[1] == "2"
        assert frames[2] == "3"
        # After reaching end, direction reverses
        assert frames[3] == "2"

    def test_empty_frames(self):
        sp = BouncingSpinner([])
        assert sp.next_frame() == ""

    def test_single_frame_bouncing(self):
        sp = BouncingSpinner(["Z"])
        assert sp.next_frame() == "Z"
        assert sp.next_frame() == "Z"

    def test_reset(self):
        sp = BouncingSpinner(["A", "B", "C"])
        sp.next_frame()
        sp.next_frame()
        sp.reset()
        assert sp.next_frame() == "A"
        assert sp._direction == 1


# ── get_spinner registry ──────────────────────────────────────────────

class TestGetSpinner:
    def test_known_name(self):
        sp = get_spinner("dots")
        assert sp is SPINNERS["dots"]

    def test_unknown_falls_back_to_dots(self):
        sp = get_spinner("nonexistent_spinner")
        assert sp is SPINNERS["dots"]

    def test_all_registry_entries_are_valid(self):
        for name, sp in SPINNERS.items():
            frame = sp.next_frame()
            assert isinstance(frame, str), f"Spinner '{name}' returned non-string"
            sp.reset()
