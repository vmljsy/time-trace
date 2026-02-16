"""
Formatter — Formatting utilities for structured data display.

Provides functions to format data structures (tables, bar charts, lists)
into display-ready strings, separate from terminal rendering logic.
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

def format_history_table(
    logs: list[dict[str, Any]],
    visible_rows: int,
    scroll_offset: int,
    selected_idx: int,
    max_task_width: int = 18,
) -> list[tuple[str, str, str | None]]:
    """Format log entries as table rows with aligned columns.
    
    Args:
        logs: List of log entry dictionaries
        visible_rows: Number of rows to display
        scroll_offset: Starting index for scrolling
        selected_idx: Index of selected entry for highlighting
        max_task_width: Maximum width for task name column
        
    Returns:
        List of tuples: (main_line, style, tags_str)
        - main_line: Formatted table row text
        - style: ANSI style code for the row (e.g., "\033[7m" for highlight)
        - tags_str: Tags string to display separately (or None)
    """
    rows = []
    
    for i in range(visible_rows):
        idx = scroll_offset + i
        if idx >= len(logs):
            break
            
        entry = logs[idx]
        style = "\033[7m" if idx == selected_idx else ""
        
        # Extract timestamp (last 8 chars = HH:MM:SS)
        ts = entry.get("start_time", "")[-8:] if entry.get("start_time") else ""
        
        # Extract and format tags
        tags_str = " ".join(f"#{t}" for t in entry.get("tags", []))
        
        # Adjust task width based on whether tags exist
        task_w = 15 if tags_str else max_task_width
        
        # Build the main line with aligned columns
        line = f" {idx + 1:2d}. {entry['task'][:task_w]:<{task_w}} | {entry['duration']:<8} | {ts}"
        
        # Return tags separately so they can be styled differently
        rows.append((line, style, tags_str if tags_str and not style else None))
    
    return rows


def format_report_bars(
    stats: dict[str, float],
    bar_width: int,
    mode: str = "project",
) -> list[tuple[str, str, str, str]]:
    """Format statistics as bar chart rows.
    
    Args:
        stats: Dictionary mapping project/tag names to seconds
        bar_width: Maximum width for the bar visualization
        mode: "project" or "tag" - affects label formatting
        
    Returns:
        List of tuples: (label, bar, duration, total_str)
        - label: Left-aligned name (project or #tag)
        - bar: Bar characters (e.g., "████████")
        - duration: Formatted duration string
        - total_str: Total duration for the period (first row only)
    """
    rows = []
    
    if not stats:
        return rows
    
    max_val = max(stats.values())
    total_period = sum(stats.values())
    total_str = str(timedelta(seconds=int(total_period)))
    
    # Add total as first "row"
    rows.append(("TOTAL", "", total_str, total_str))
    
    for name, seconds in stats.items():
        pct = seconds / max_val if max_val > 0 else 0
        bar_len = int(pct * bar_width)
        duration = str(timedelta(seconds=int(seconds)))
        
        # Format label based on mode
        label = f"#{name}" if mode == "tag" else name
        label = f"{label[:15]:<15}"  # Truncate and left-align
        
        bar = "█" * bar_len
        
        rows.append((label, bar, duration, ""))
    
    return rows


def format_config_list(
    config_options: list[tuple[str, str | None, str, str, Any]],
    current_config: dict[str, Any],
) -> list[tuple[str, str, bool]]:
    """Format configuration options as a categorized list.
    
    Args:
        config_options: List of (category, key, label, type, choices)
        current_config: Current configuration values
        
    Returns:
        List of tuples: (text, display_type, is_category)
        - text: Formatted text to display
        - display_type: "category" or "option"
        - is_category: True if this is a category header
    """
    rows = []
    last_cat = ""
    
    for opt in config_options:
        cat, key, label, opt_type, choices = opt
        
        # Add category header if changed
        if cat != last_cat:
            rows.append((f"[{cat}]", "category", True))
            last_cat = cat
        
        # Format the option label with current value
        if opt_type == "bool":
            value_str = "ON" if current_config.get(key, False) else "OFF"
            formatted_label = f"{label}: {value_str}"
        elif opt_type == "cycle":
            value = current_config.get(key)
            formatted_label = f"{label}: {value}"
        else:
            # Info-only fields
            formatted_label = label
        
        rows.append((f"{formatted_label:<40}", "option", False))
    
    return rows
