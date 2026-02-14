#!/usr/bin/env python3
"""
TimeTrace v0.5.0 — Entry Point (backward-compatible).

Usage:
    python trace.py
"""

from timetrace.database import TimeTrace
from timetrace.tui import TraceTUI


def main() -> None:
    try:
        TraceTUI(TimeTrace()).run()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
