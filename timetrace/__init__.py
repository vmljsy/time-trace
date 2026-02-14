"""
TimeTrace v0.5.0 — A zero-dependency TUI time tracker.
"""

__version__ = "0.5.0"
VERSION = __version__

from timetrace.database import TimeTrace
from timetrace.tui import TraceTUI
from timetrace.console import Console
from timetrace.platform import Platform
from timetrace.config import ConfigManager, THEMES, TIME_FORMAT
from timetrace.hooks import HookManager, Notifier
from timetrace.utils import parse_tags, parse_time_input

__all__ = [
    "VERSION",
    "TimeTrace",
    "TraceTUI",
    "Console",
    "Platform",
    "ConfigManager",
    "THEMES",
    "TIME_FORMAT",
    "HookManager",
    "Notifier",
    "parse_tags",
    "parse_time_input",
]
