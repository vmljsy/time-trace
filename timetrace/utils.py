"""
Utilities — Tag parsing and flexible timestamp parsing.
"""

from __future__ import annotations

import re
from datetime import datetime

from timetrace.config import TIME_FORMAT


def parse_tags(text: str) -> tuple[str, list[str]]:
    """Extract ``#tags`` from *text*.

    Returns ``(clean_name, [lowered_tags])``.  The clean name has all
    ``#tag`` tokens stripped out.
    """
    tags = re.findall(r"#([\w-]+)", text)
    clean = re.sub(r"\s*#[\w-]+", "", text).strip()
    return clean, [t.lower() for t in tags]


def parse_time_input(text: str) -> tuple[str | None, str | None]:
    """Smart timestamp parser accepting flexible human input.

    Accepted formats (most-specific first):
    - ``2026-02-14 14:30:00`` — full timestamp
    - ``2026-02-14 14:30``    — no seconds
    - ``14:30:00``            — time only (today assumed)
    - ``14:30``               — time only, no seconds

    Returns ``(formatted_string, error)``.  *error* is ``None`` on
    success.  Both values are ``None`` if *text* is blank.
    """
    text = text.strip()
    if not text:
        return None, None  # blank — let the caller decide on a default

    formats = [
        (TIME_FORMAT, text),        # Full: 2026-02-14 14:30:00
        ("%Y-%m-%d %H:%M", text),   # No seconds: 2026-02-14 14:30
        ("%H:%M:%S", text),         # Time only with seconds
        ("%H:%M", text),            # Time only
    ]

    for fmt, val in formats:
        try:
            dt = datetime.strptime(val, fmt)
            if fmt in ("%H:%M:%S", "%H:%M"):
                now = datetime.now()
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
            return dt.strftime(TIME_FORMAT), None
        except ValueError:
            continue

    return None, "Format: 14:30 or YYYY-MM-DD HH:MM:SS"
