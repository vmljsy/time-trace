"""
Platform — OS-specific helpers for app directory and idle detection.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys


class Platform:
    """Static helpers that abstract away OS differences."""

    @staticmethod
    def get_app_dir() -> str:
        """Return (and create) the application data directory."""
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            path = os.path.join(base, "TimeTrace")
        else:
            path = os.path.join(os.path.expanduser("~"), ".timetrace")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def get_idle_seconds() -> float:
        """Best-effort idle time in seconds.  Returns 0.0 on failure."""
        try:
            if os.name == "nt":
                class _LastInputInfo(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

                lii = _LastInputInfo(cbSize=ctypes.sizeof(_LastInputInfo))
                if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):  # type: ignore[attr-defined]
                    tick = ctypes.windll.kernel32.GetTickCount()  # type: ignore[attr-defined]
                    return (tick - lii.dwTime) / 1000.0
            elif sys.platform == "darwin":
                raw = subprocess.check_output(
                    "ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF; exit}'",
                    shell=True,
                )
                return int(raw) / 1e9
            else:
                return int(subprocess.check_output("xprintidle", shell=True)) / 1000.0
        except Exception:
            return 0.0
