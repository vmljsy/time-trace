"""
Formatter — Unified formatting utilities for structured data display.

Provides a flexible TableFormatter class to generate aligned, styled rows
from lists of dictionaries, supporting custom alignment, separators, 
column hooks, and header generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Callable, List, Optional, Tuple


@dataclass
class Column:
    """Definition of a table column."""
    key: str
    label: str
    width: int
    align: str = "<"  # < (left), > (right), ^ (center)
    formatter: Optional[Callable[[Any, dict[str, Any]], str]] = None


class TableFormatter:
    """Unified engine for formatting tabular data."""
    
    def __init__(
        self, 
        columns: List[Column], 
        sep: str = " | ",
        show_header: bool = False
    ) -> None:
        self.columns = columns
        self.sep = sep
        self.show_header = show_header

    def format_batch(
        self, 
        data: List[dict[str, Any]],
        row_style_provider: Optional[Callable[[int, dict[str, Any]], str]] = None
    ) -> List[Tuple[str, str]]:
        """Format a list of dictionaries into lines and styles."""
        rows = []
        
        if self.show_header:
            header_parts = []
            for col in self.columns:
                fmt = f"{{:{col.align}{col.width}}}"
                header_parts.append(fmt.format(col.label[:col.width]))
            rows.append((self.sep.join(header_parts), "\033[1m"))

        for i, entry in enumerate(data):
            row_parts = []
            for col in self.columns:
                val = entry.get(col.key, "")
                if col.formatter:
                    val = col.formatter(val, entry)
                
                val_str = str(val)[:col.width]
                fmt = f"{{:{col.align}{col.width}}}"
                row_parts.append(fmt.format(val_str))
            
            line = self.sep.join(row_parts)
            style = row_style_provider(i, entry) if row_style_provider else ""
            rows.append((line, style))
            
        return rows


# ------------------------------------------------------------------
# specialized wrappers (to keep TUI compatibility for now)
# ------------------------------------------------------------------

def format_history_table(
    logs: list[dict[str, Any]],
    visible_rows: int,
    scroll_offset: int,
    selected_idx: int,
) -> list[tuple[str, str, str | None]]:
    """Refactored history table using the unified TableFormatter class."""
    
    # 1. Prepare data
    display_data = []
    for i, log in enumerate(logs):
        item = log.copy()
        item["_idx"] = i + 1
        display_data.append(item)
    
    # 2. Define columns to match original TUI exactly
    # Original: f" {idx + 1:2d}. {entry['task'][:max_task_w]:<{max_task_w}} | {entry['duration']:<8} | {ts}"
    # Note: The first column includes the leading space and following dot+space.
    columns = [
        Column("_idx", "#", 4, ">", lambda v, _: f" {v}."),
        Column("task", "Task", 18, "<", lambda v, e: str(v)[:15] if e.get("tags") else str(v)[:18]),
        Column("duration", "Time", 8, "<"),
        Column("start_time", "Start", 8, "<", lambda v, _: str(v)[-8:] if v else ""),
    ]
    
    formatter = TableFormatter(columns, sep=" | ")
    
    # 3. Slice and Style
    paginated_data = display_data[scroll_offset:scroll_offset + visible_rows]
    
    def get_style(i: int, entry: dict[str, Any]) -> str:
        return "\033[7m" if (scroll_offset + i) == selected_idx else ""

    formatted = formatter.format_batch(paginated_data, row_style_provider=get_style)
    
    # 4. Convert and fix separators for specific TUI look
    result = []
    for i, (line, style) in enumerate(formatted):
        actual_idx = scroll_offset + i
        entry = logs[actual_idx]
        tags_raw = entry.get("tags", [])
        tags_str = " ".join(f"#{t}" for t in tags_raw) if tags_raw else None
        
        # Original had "  1. task" (no pipe after index)
        line = line.replace(" | ", " ", 1)
        
        result.append((line, style, tags_str if not style else None))
        
    return result


def format_report_bars(
    stats: dict[str, float],
    bar_width: int,
    mode: str = "project",
) -> list[tuple[str, str, str, str]]:
    """Refactored report bars using the unified logic principles."""
    if not stats: return []

    max_val = max(stats.values())
    total_period = sum(stats.values())
    total_period_str = str(timedelta(seconds=int(total_period)))

    data = [{"name": n, "sec": s, "dur": str(timedelta(seconds=int(s)))} for n, s in stats.items()]
    
    # We still return the specialized tuple (label, bar, dur, total) for TUI compatibility
    result = [("TOTAL", "", total_period_str, total_period_str)]
    for entry in data:
        label = f"#{entry['name']}" if mode == "tag" else entry['name']
        bar = "█" * int((entry["sec"] / max_val) * bar_width) if max_val > 0 else ""
        result.append((f"{label[:15]:<15}", bar, entry['dur'], ""))
    
    return result


def format_config_list(
    config_options: list[tuple[str, str | None, str, str, Any]],
    current_config: dict[str, Any],
) -> list[tuple[str, str, bool]]:
    """Legacy wrapper for config formatting."""
    rows = []
    last_cat = ""
    for cat, key, label, opt_type, choices in config_options:
        if cat != last_cat:
            rows.append((f"[{cat}]", "category", True))
            last_cat = cat
        val = ""
        if opt_type == "bool": val = "ON" if current_config.get(key, False) else "OFF"
        elif opt_type == "cycle": val = str(current_config.get(key))
        lbl = f"{label}: {val}" if val else label
        rows.append((f"{lbl:<40}", "option", False))
    return rows
