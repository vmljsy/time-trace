"""
TUI — Terminal User Interface for TimeTrace.

Handles all screen drawing and keyboard input routing.  Each "mode"
corresponds to a different screen (dashboard, reports, history, etc.).
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any

if os.name == "nt":
    import msvcrt

from timetrace import VERSION
from timetrace.config import THEMES, TIME_FORMAT
from timetrace.console import Console
from timetrace.database import TimeTrace
from timetrace.platform import Platform
from timetrace.utils import parse_time_input


class TraceTUI:
    """Interactive terminal UI for TimeTrace."""

    def __init__(self, app: TimeTrace) -> None:
        self.app = app
        self.console = Console()

        # State
        self.mode: str = "DASH"
        self.selected_idx: int = 0
        self.config_idx: int = 0
        self.input_text: str = ""

        # Rate-limiting caches
        self.last_idle_check: float = 0
        self.cached_idle: float = 0
        self.last_today_update: float = 0
        self.cached_today: str = app.get_today_total()
        self.cached_stats: dict[str, float] = {}
        self.last_stats_update: float = 0
        self.report_period: str = "today"
        self.report_mode: str = "project"  # "project" or "tag"

        cfg = app.get_config()
        self.cached_heatmap = app.get_heatmap_matrix(
            cfg.get("heatmap_days", 7),
            cfg.get("heatmap_start", 6),
            cfg.get("heatmap_end", 23),
            cfg.get("heatmap_weekdays", "MTWTFSS"),
        )
        self.last_heatmap_update: float = time.time()

        self.tag_filter: str | None = None

        # Temporary state for multi-step flows
        self.config_options: list[tuple[str, str | None, str, str, Any]] = []
        self.temp_time: int = 0
        self.edit_entry: dict[str, Any] = {}
        self.edit_new_task: str = ""
        self.edit_new_start: str = ""
        self.edit_new_end: str = ""
        self.edit_error: str = ""
        self.add_new_task: str = ""
        self.add_new_start: str = ""
        self.add_new_end: str = ""
        self.add_error: str = ""

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Enter the TUI event loop (blocks until quit)."""
        # Alternate screen buffer + hide cursor
        sys.stdout.write("\033[?1049h\033[?25l")
        sys.stdout.flush()
        try:
            while True:
                self._draw()
                self._input()
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write("\033[?1049l\033[?25h")
            sys.stdout.flush()

    # ==================================================================
    # DRAWING
    # ==================================================================
    def _draw(self) -> None:
        self.console._get_size()
        self.console.clear_buffer()

        h, w = self.console.height, self.console.width
        cfg = self.app.get_config()
        theme = THEMES.get(cfg.get("theme", "Default"), THEMES["Default"])

        # Rate-limited background updates
        now = time.time()
        if now - self.last_idle_check > 2.0:
            self.cached_idle = Platform.get_idle_seconds()
            self.last_idle_check = now
        if now - self.last_today_update > 60.0:
            self.cached_today = self.app.get_today_total()
            self.last_today_update = now
        if self.mode == "REPORTS" and (now - self.last_stats_update > 5.0 or not self.cached_stats):
            if self.report_mode == "tag":
                self.cached_stats = self.app.get_tag_stats(self.report_period)
            else:
                self.cached_stats = self.app.get_project_stats(self.report_period)
            self.last_stats_update = now
        if self.mode == "DASH" and now - self.last_heatmap_update > 60.0:
            self.cached_heatmap = self.app.get_heatmap_matrix(
                cfg.get("heatmap_days", 7),
                cfg.get("heatmap_start", 6),
                cfg.get("heatmap_end", 23),
                cfg.get("heatmap_weekdays", "MTWTFSS"),
            )
            self.last_heatmap_update = now

        active = self.app.get_active()
        projects = self.app.get_projects()
        history = self.app.get_recent_history()

        # --- Header ---
        self.console.print_at(1, 2, f"🏁 TIMETRACE v{VERSION}", theme["header"])
        self.console.print_at(1, w - 20, f"📅 Today: {self.cached_today}", theme["header"])

        # --- Box border ---
        self.console.print_at(3, 1, "┌" + "─" * (w - 4) + "┐", theme["box"])
        for y in range(4, h - 2):
            self.console.print_at(y, 1, "│", theme["box"])
            self.console.print_at(y, w - 2, "│", theme["box"])
        self.console.print_at(h - 2, 1, "└" + "─" * (w - 4) + "┘", theme["box"])

        # --- Mode-specific content ---
        if self.mode == "SELECT":
            self._draw_select(projects, theme)
        elif self.mode == "INPUT":
            self._draw_input(h, w)
        elif self.mode == "REPORTS":
            self._draw_reports(h, w, theme)
        elif self.mode == "FORGOT":
            self._draw_forgot(h, w)
        elif self.mode == "FORGOT_TASK":
            self._draw_forgot_task(h, w)
        elif self.mode == "HISTORY":
            self._draw_history(h, w, theme)
        elif self.mode in ("EDIT_TASK", "EDIT_START", "EDIT_END"):
            self._draw_edit(h, w)
        elif self.mode in ("ADD_TASK", "ADD_START", "ADD_END"):
            self._draw_add(h, w)
        elif self.mode == "TAG_FILTER":
            self._draw_tag_filter(h, w)
        elif self.mode == "CONFIG":
            self._draw_config(h, w, theme)
        elif self.mode == "HELP":
            self._draw_help(h, w, theme)
        else:
            self._draw_dashboard(h, w, active, history, cfg, theme)

        # --- Footer ---
        self.console.print_at(h - 2, 2, self._footer_text(), "\033[7m")
        self.console.draw()

    # ------------------------------------------------------------------
    # Draw helpers — each mode gets its own method for clarity
    # ------------------------------------------------------------------
    def _draw_select(self, projects: list[str], theme: dict[str, str]) -> None:
        self.console.print_at(4, 4, "📁 SELECT RECENT PROJECT:", "\033[1m")
        for i, p in enumerate(projects):
            style = "\033[7m" if i == self.selected_idx else ""
            self.console.print_at(6 + i, 6, f" {p} ", style)

    def _draw_input(self, h: int, w: int) -> None:
        self.console.print_at(h // 2 - 2, w // 2 - 10, "📝 NEW TASK NAME:", "\033[1m")
        self.console.print_at(h // 2, w // 2 - 15, f" {self.input_text + '_'} ", "\033[7m")
        self.console.print_at(h // 2 + 2, w // 2 - 15, "Use #tags inline (e.g. #meeting)", "\033[2m")

    def _draw_reports(self, h: int, w: int, theme: dict[str, str]) -> None:
        p_map = {"today": "TODAY", "week": "WEEK", "month": "MONTH", "all": "ALL"}
        tab_str = ""
        for k, v in p_map.items():
            tab_str += f"[{v}] " if self.report_period == k else f" {v}  "

        mode_label = "BY TAG" if self.report_mode == "tag" else "BY PROJECT"
        self.console.print_at(4, 4, f"📊 REPORT ({mode_label}): {tab_str}", "\033[1m")
        self.console.print_at(4, w - 30, "1-4 filter  5 toggle view", "\033[2m")

        row = 6
        max_val = max(self.cached_stats.values()) if self.cached_stats else 1
        bar_width = w - 40
        total_period = sum(self.cached_stats.values())

        self.console.print_at(row, 6, f"TOTAL: {str(timedelta(seconds=int(total_period)))}", theme["highlight"])
        row += 2

        for p, sec in self.cached_stats.items():
            if row >= h - 4:
                break
            pct = sec / max_val
            bar_len = int(pct * bar_width)
            dur = str(timedelta(seconds=int(sec)))
            label = f"#{p}" if self.report_mode == "tag" else p
            self.console.print_at(row, 6, f"{label[:15]:<15}")
            self.console.print_at(row, 22, "█" * bar_len, theme["bar"])
            self.console.print_at(row, 22 + bar_len + 1, dur)
            row += 2

    def _draw_forgot(self, h: int, w: int) -> None:
        self.console.print_at(h // 2 - 3, w // 2 - 15, "🕰️  RETROACTIVE START", "\033[1;33m")
        self.console.print_at(h // 2 - 1, w // 2 - 20, "How long ago did you start? (mins)", "\033[1m")
        self.console.print_at(h // 2, w // 2 - 5, f" {self.input_text + '_'} ", "\033[7m")
        self.console.print_at(h // 2 + 2, w // 2 - 20, "Enter task name after time...", "\033[2m")

    def _draw_forgot_task(self, h: int, w: int) -> None:
        self.console.print_at(h // 2 - 3, w // 2 - 15, "🕰️  RETROACTIVE START", "\033[1;33m")
        self.console.print_at(h // 2 - 1, w // 2 - 20, f"Starting {self.temp_time} mins ago...", "\033[1;32m")
        self.console.print_at(h // 2 + 1, w // 2 - 10, "Task Name:", "\033[1m")
        self.console.print_at(h // 2 + 2, w // 2 - 15, f" {self.input_text + '_'} ", "\033[7m")

    def _draw_history(self, h: int, w: int, theme: dict[str, str]) -> None:
        self.console.print_at(4, 4, "📜 HISTORY MANAGER", "\033[1;33m")
        self.console.print_at(4, w - 55, "[a] Add [e] Edit [del] Delete [x] Export [g] Tag filter", "\033[2m")

        if self.tag_filter:
            self.console.print_at(5, 6, f"🏷️ Filtered: #{self.tag_filter}  (press g to clear)", "\033[1;36m")

        all_logs = self.app.get_recent_history(limit=50)
        logs = [e for e in all_logs if self.tag_filter in e.get("tags", [])] if self.tag_filter else all_logs
        visible_rows = h - 10 if self.tag_filter else h - 9
        scroll_offset = max(0, self.selected_idx - visible_rows + 1)
        row_start = 7 if self.tag_filter else 6

        for i in range(visible_rows):
            idx = scroll_offset + i
            if idx >= len(logs):
                break
            entry = logs[idx]
            style = "\033[7m" if idx == self.selected_idx else ""
            ts = entry.get("start_time", "")[-8:] if entry.get("start_time") else ""
            tags_str = " ".join(f"#{t}" for t in entry.get("tags", []))
            max_task_w = 15 if tags_str else 18
            line = f" {idx + 1:2d}. {entry['task'][:max_task_w]:<{max_task_w}} | {entry['duration']:<8} | {ts}"
            self.console.print_at(row_start + i, 6, line, style)
            if tags_str and not style:
                self.console.print_at(row_start + i, 6 + len(line) + 1, tags_str[:20], "\033[36m")

        self.console.print_at(h - 4, 6, f"Entries: {len(logs)}  Selected: {self.selected_idx + 1}", "\033[2m")

    def _draw_edit(self, h: int, w: int) -> None:
        cx, cy = w // 2 - 22, h // 2 - 6
        self.console.print_at(cy, cx, "✏️  EDIT LOG ENTRY", "\033[1;33m")
        if self.edit_entry:
            self.console.print_at(cy + 2, cx, f"Task:  {self.edit_entry['task']}", "\033[2m")
            self.console.print_at(cy + 3, cx, f"Start: {self.edit_entry['start_time']}", "\033[2m")
            self.console.print_at(cy + 4, cx, f"End:   {self.edit_entry['stop_time']}", "\033[2m")
            self.console.print_at(cy + 5, cx, f"Dur:   {self.edit_entry['duration']}", "\033[2m")

        prompts = {"EDIT_TASK": "New Task Name:", "EDIT_START": "New Start Time:", "EDIT_END": "New End Time:"}
        hints = {
            "EDIT_TASK": "Enter=confirm, blank=keep current",
            "EDIT_START": "14:30 | 2026-01-15 14:30 | blank=keep",
            "EDIT_END": "14:30 | 2026-01-15 14:30 | blank=keep",
        }
        self.console.print_at(cy + 7, cx, prompts[self.mode], "\033[1m")
        self.console.print_at(cy + 8, cx, f" {self.input_text + '_'} ", "\033[7m")
        self.console.print_at(cy + 10, cx, hints[self.mode], "\033[2m")
        if self.edit_error:
            self.console.print_at(cy + 12, cx, f"⚠ {self.edit_error}", "\033[1;31m")

    def _draw_add(self, h: int, w: int) -> None:
        cx, cy = w // 2 - 22, h // 2 - 6
        self.console.print_at(cy, cx, "➕ ADD NEW ENTRY", "\033[1;33m")
        steps = {"ADD_TASK": "Step 1/3", "ADD_START": "Step 2/3", "ADD_END": "Step 3/3"}
        self.console.print_at(cy, cx + 25, steps[self.mode], "\033[2m")

        if self.add_new_task:
            self.console.print_at(cy + 2, cx, f"Task:  {self.add_new_task}", "\033[32m")
        if self.add_new_start:
            self.console.print_at(cy + 3, cx, f"Start: {self.add_new_start}", "\033[32m")
        if self.add_new_end:
            self.console.print_at(cy + 4, cx, f"End:   {self.add_new_end}", "\033[32m")

        prompts = {"ADD_TASK": "Task Name:", "ADD_START": "Start Time:", "ADD_END": "End Time:"}
        self.console.print_at(cy + 7, cx, prompts[self.mode], "\033[1m")
        self.console.print_at(cy + 8, cx, f" {self.input_text + '_'} ", "\033[7m")
        if self.mode != "ADD_TASK":
            self.console.print_at(cy + 10, cx, "14:30 | 2026-01-15 14:30 | Enter=default", "\033[2m")
        if self.add_error:
            self.console.print_at(cy + 12, cx, f"⚠ {self.add_error}", "\033[1;31m")

    def _draw_tag_filter(self, h: int, w: int) -> None:
        self.console.print_at(4, 4, "🏷️ SELECT TAG TO FILTER:", "\033[1;36m")
        all_tags = self.app.get_all_tags()
        if not all_tags:
            self.console.print_at(6, 6, "No tags found. Use #tags when creating tasks.", "\033[2m")
        else:
            visible = h - 10
            scroll_off = max(0, self.selected_idx - visible + 1)
            for i in range(visible):
                idx = scroll_off + i
                if idx >= len(all_tags):
                    break
                style = "\033[7m" if idx == self.selected_idx else ""
                self.console.print_at(6 + i, 6, f" #{all_tags[idx]} ", style)
            self.console.print_at(h - 4, 6, f"Tags: {len(all_tags)}  Selected: {self.selected_idx + 1}", "\033[2m")

    def _draw_config(self, h: int, w: int, theme: dict[str, str]) -> None:
        cfg = self.app.get_config()
        self.config_options = [
            ("BEHAVIOR", "idle_threshold", f"Idle Warning: {cfg.get('idle_threshold')}s", "cycle", [10, 30, 60, 300, 600, 1800]),
            ("BEHAVIOR", "auto_backup", f"Auto Backup: {'ON' if cfg.get('auto_backup') else 'OFF'}", "bool", None),
            ("BEHAVIOR", "backup_freq", f"Backup Freq: {cfg.get('backup_freq')}", "cycle", ["STOP", "DAILY", "WEEKLY"]),
            ("VISUAL", "heatmap_days", f"Heatmap Rows: {cfg.get('heatmap_days')}", "cycle", [7, 14, 28]),
            ("VISUAL", "heatmap_start", f"Heatmap Start: {cfg.get('heatmap_start')}h", "cycle", [0, 6, 7, 8, 9, 10]),
            ("VISUAL", "heatmap_end", f"Heatmap End: {cfg.get('heatmap_end')}h", "cycle", [17, 18, 20, 22, 23]),
            ("VISUAL", "heatmap_weekdays", f"Heatmap Days: {cfg.get('heatmap_weekdays')}", "cycle", ["MTWTFSS", "MTWTF--", "-----SS"]),
            ("VISUAL", "theme", f"Theme: {cfg.get('theme')}", "cycle", list(THEMES.keys())),
            ("FEATURES", "feature_billing", f"Billing: {'ON' if cfg.get('feature_billing') else 'OFF'}", "bool", None),
            ("FEATURES", "feature_html_report", f"HTML Reports: {'ON' if cfg.get('feature_html_report') else 'OFF'}", "bool", None),
            ("FEATURES", "notifications", f"Notifications: {'ON' if cfg.get('notifications', True) else 'OFF'}", "bool", None),
            ("CORE", None, f"DB Path: {self.app.db_path[-30:]}", "info", None),
            ("CORE", None, f"Webhooks: {len(cfg.get('on_stop', []))} Active", "info", None),
        ]

        self.console.print_at(4, 4, "⚙️  CONFIGURATION", "\033[1;35m")
        self.console.print_at(4, w - 25, "[Enter] Toggle/Edit", "\033[2m")

        last_cat = ""
        row = 6
        for i, opt in enumerate(self.config_options):
            cat, _key, label, _typ, _choices = opt
            if row >= h - 3:
                break
            if cat != last_cat:
                self.console.print_at(row, 6, f"[{cat}]", "\033[1;90m")
                row += 1
                last_cat = cat
            style = "\033[7m" if i == self.config_idx else ""
            self.console.print_at(row, 8, f"{label:<40}", style)
            row += 1

    def _draw_help(self, h: int, w: int, theme: dict[str, str]) -> None:
        """Render the help / keybindings reference screen."""
        self.console.print_at(4, 4, "❓ KEYBINDING REFERENCE", "\033[1;35m")
        self.console.print_at(4, w - 20, f"v{VERSION}", "\033[2m")

        bindings = [
            ("DASHBOARD", [
                ("s", "Select recent project"),
                ("n", "New task (type name)"),
                ("t", "Stop active task"),
                ("r", "Reports view"),
                ("f", "Forgot — retroactive start"),
                ("h", "History manager"),
                ("c", "Configuration"),
                ("b", "Manual backup now"),
                ("?", "This help screen"),
                ("q", "Quit"),
            ]),
            ("HISTORY", [
                ("↑/↓", "Navigate entries"),
                ("a", "Add new entry"),
                ("e", "Edit selected entry"),
                ("d/DEL", "Delete selected entry"),
                ("x", "Export to CSV"),
                ("g", "Filter by tag"),
                ("q", "Back to dashboard"),
            ]),
            ("REPORTS", [
                ("1-4", "Period: Today/Week/Month/All"),
                ("5", "Toggle Project ↔ Tag view"),
                ("q", "Back to dashboard"),
            ]),
        ]

        row = 6
        for section, keys in bindings:
            if row >= h - 4:
                break
            self.console.print_at(row, 6, f"[{section}]", "\033[1;90m")
            row += 1
            for key, desc in keys:
                if row >= h - 4:
                    break
                self.console.print_at(row, 8, f"{key:>8}  {desc}")
                row += 1
            row += 1

    def _draw_dashboard(
        self,
        h: int,
        w: int,
        active: Any,
        history: list[dict[str, Any]],
        cfg: dict[str, Any],
        theme: dict[str, str],
    ) -> None:
        if active and active["action"] == "START":
            start_t = datetime.strptime(active["timestamp"], TIME_FORMAT)
            dur = str(datetime.now() - start_t).split(".")[0]
            started_at = start_t.strftime("%H:%M")
            active_tags = self.app._cache_active_tags
            tags_str = " ".join(f"#{t}" for t in active_tags) if active_tags else ""
            self.console.print_at(5, 4, f"▶️ ACTIVE: {active['task']}", theme["highlight"])
            if tags_str:
                self.console.print_at(5, 14 + len(active["task"]), f" {tags_str}", "\033[36m")
            self.console.print_at(6, 4, f"⏱️ RUNNING: {dur}  (since {started_at})", theme["highlight"])

            threshold = cfg.get("idle_threshold", 300)
            if self.cached_idle > threshold:
                self.console.print_at(6, 45, f"⚠️ IDLE: {int(self.cached_idle)}s", theme["warn"])

            today_sessions = len([
                e for e in history
                if e.get("start_time", "")[:10] == datetime.now().strftime("%Y-%m-%d")
            ])
            self.console.print_at(7, 4, f"📈 Today: {self.cached_today} total  •  {today_sessions} sessions", "\033[2m")
        else:
            self.console.print_at(5, 4, "💤 STATUS: IDLE", "\033[2m")
            today_sessions = len([
                e for e in history
                if e.get("start_time", "")[:10] == datetime.now().strftime("%Y-%m-%d")
            ])
            self.console.print_at(6, 4, f"📈 Today: {self.cached_today} total  •  {today_sessions} sessions", "\033[2m")

        # History (left column)
        self.console.print_at(9, 4, "📜 RECENT SESSIONS:", "\033[1;33m")
        for i, entry in enumerate(history):
            tags_str = " ".join(f"#{t}" for t in entry.get("tags", []))
            line = f"• {entry['task']:<20} | {entry['duration']}"
            self.console.print_at(11 + i, 6, line)
            if tags_str:
                self.console.print_at(11 + i, 6 + len(line) + 1, tags_str[:20], "\033[36m")

        # Heatmap (right column)
        mid_x = w // 2 + 2
        if mid_x < w - 20:
            self.console.print_at(9, mid_x, "🔥 ACTIVITY:", "\033[1;33m")
            s_h = cfg.get("heatmap_start", 8)
            e_h = cfg.get("heatmap_end", 20)
            hour_label = "    "
            for hr in range(s_h, e_h + 1):
                hour_label += f"{hr:02d}" if hr % 3 == 0 else "  "
            self.console.print_at(10, mid_x, hour_label, "\033[2m")

            hm_chars = ["·", "░", "▒", "▓", "█"]
            hm_styles = ["\033[2m", "\033[32m", "\033[32m", "\033[1;32m", "\033[1;32m"]
            if theme == THEMES["Dark"]:
                hm_styles = ["\033[2m", "\033[34m", "\033[34m", "\033[1;34m", "\033[1;34m"]

            hm_row = 11
            if self.cached_heatmap:
                for label, slots in self.cached_heatmap:
                    if hm_row >= h - 3:
                        break
                    self.console.print_at(hm_row, mid_x, label, "\033[2m")
                    for i, val in enumerate(slots):
                        self.console.print_at(hm_row, mid_x + 5 + i * 2, hm_chars[val], hm_styles[val])
                    hm_row += 1

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    def _footer_text(self) -> str:
        _INPUT_MODES = {"INPUT", "FORGOT", "FORGOT_TASK", "EDIT_TASK", "EDIT_START", "EDIT_END", "ADD_TASK", "ADD_START", "ADD_END"}
        if self.mode == "REPORTS":
            return " [1] Today [2] Week [3] Month [4] All [5] Toggle Tag/Project  [q] Back "
        if self.mode == "HISTORY":
            return " [UP/DN] Scroll  [a] Add  [e] Edit  [del/d] Delete  [x] Export  [g] Tags  [q] Back "
        if self.mode == "TAG_FILTER":
            return " [UP/DOWN] Select  [Enter] Filter  [q] Back "
        if "EDIT_" in self.mode or "ADD_" in self.mode:
            return " [Enter] Confirm  [Esc] Cancel "
        if self.mode == "CONFIG":
            return " [UP/DOWN] Select  [Enter] Toggle  [q] Back "
        if "FORGOT" in self.mode:
            return " [Enter] Confirm  [Esc] Cancel "
        if self.mode == "HELP":
            return " [q] Back to Dashboard "
        # Dashboard
        return " [s] Select  [n] New  [t] Stop  [r] Reports  [f] Forgot  [h] Hist  [c] Conf  [b] Backup  [?] Help  [q] Quit "

    # ==================================================================
    # INPUT HANDLING
    # ==================================================================
    def _input(self) -> None:
        has_input = False
        if os.name == "nt":
            if msvcrt.kbhit():
                has_input = True
        else:
            has_input = True

        if not has_input:
            time.sleep(0.1)
            return

        ch = self.console.get_key()

        # Global back / quit
        _INPUT_MODES = {
            "INPUT", "FORGOT", "FORGOT_TASK",
            "EDIT_TASK", "EDIT_START", "EDIT_END",
            "ADD_TASK", "ADD_START", "ADD_END",
        }
        if ch == "q" and self.mode not in _INPUT_MODES:
            if self.mode == "DASH":
                if os.name == "nt":
                    os.system("cls")
                else:
                    os.system("clear")
                print("\033[?25h\033[0m")
                sys.exit(0)
            elif self.mode == "TAG_FILTER":
                self.mode = "HISTORY"
                return
            else:
                self.mode = "DASH"
                self.tag_filter = None
                return

        # Dispatch to mode handler
        handler = {
            "DASH": self._input_dash,
            "REPORTS": self._input_reports,
            "CONFIG": self._input_config,
            "SELECT": self._input_select,
            "INPUT": self._input_new_task,
            "FORGOT": self._input_forgot,
            "FORGOT_TASK": self._input_forgot_task,
            "HISTORY": self._input_history,
            "TAG_FILTER": self._input_tag_filter,
            "EDIT_TASK": self._input_edit_task,
            "EDIT_START": self._input_edit_start,
            "EDIT_END": self._input_edit_end,
            "ADD_TASK": self._input_add_task,
            "ADD_START": self._input_add_start,
            "ADD_END": self._input_add_end,
            "HELP": self._input_help,
        }.get(self.mode)
        if handler:
            handler(ch)

    # ------------------------------------------------------------------
    # Per-mode input handlers
    # ------------------------------------------------------------------
    def _input_dash(self, ch: str) -> None:
        if ch == "s":
            self.mode = "SELECT"
            self.selected_idx = 0
        elif ch == "n":
            self.mode = "INPUT"
            self.input_text = ""
        elif ch == "t":
            self.app.stop()
        elif ch == "r":
            self.mode = "REPORTS"
        elif ch == "f":
            self.mode = "FORGOT"
            self.input_text = ""
        elif ch == "h":
            self.mode = "HISTORY"
            self.selected_idx = 0
        elif ch == "c":
            self.mode = "CONFIG"
            self.config_idx = 0
        elif ch == "b":
            self.app.backup_db()
        elif ch == "?":
            self.mode = "HELP"

    def _input_reports(self, ch: str) -> None:
        period_map = {"1": "today", "2": "week", "3": "month", "4": "all"}
        if ch in period_map:
            self.report_period = period_map[ch]
            self.cached_stats = {}
        elif ch == "5":
            self.report_mode = "tag" if self.report_mode == "project" else "project"
            self.cached_stats = {}

    def _input_config(self, ch: str) -> None:
        cat, key, label, typ, choices = self.config_options[self.config_idx]
        if ch == "UP":
            self.config_idx = max(0, self.config_idx - 1)
        elif ch == "DOWN":
            self.config_idx = min(len(self.config_options) - 1, self.config_idx + 1)
        elif ch in ("\r", "\n") and key:
            curr = self.app.get_config().get(key)
            if typ == "bool":
                self.app.update_config(key, not curr)
            elif typ == "cycle":
                try:
                    idx = choices.index(curr)
                except (ValueError, AttributeError):
                    idx = 0
                self.app.update_config(key, choices[(idx + 1) % len(choices)])

    def _input_select(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "DASH"
        elif ch == "UP":
            self.selected_idx = max(0, self.selected_idx - 1)
        elif ch == "DOWN":
            self.selected_idx = min(len(self.app.get_projects()) - 1, self.selected_idx + 1)
        elif ch in ("\r", "\n"):
            projects = self.app.get_projects()
            if projects:
                self.app.start(projects[self.selected_idx])
            self.mode = "DASH"

    def _input_new_task(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "DASH"
        elif ch in ("\r", "\n"):
            self.app.start(self.input_text)
            self.mode = "DASH"
        elif ch in ("\x08", "\x7f"):
            self.input_text = self.input_text[:-1]
        elif len(ch) == 1 and ch.isprintable():
            self.input_text += ch

    def _input_forgot(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "DASH"
        elif ch in ("\r", "\n"):
            if self.input_text.isdigit():
                self.temp_time = int(self.input_text)
                self.mode = "FORGOT_TASK"
                self.input_text = ""
            else:
                self.mode = "DASH"
        elif ch in ("\x08", "\x7f"):
            self.input_text = self.input_text[:-1]
        elif len(ch) == 1 and ch.isdigit():
            self.input_text += ch

    def _input_forgot_task(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "DASH"
        elif ch in ("\r", "\n"):
            self.app.start_retroactive(self.input_text, self.temp_time)
            self.mode = "DASH"
        elif ch in ("\x08", "\x7f"):
            self.input_text = self.input_text[:-1]
        elif len(ch) == 1 and ch.isprintable():
            self.input_text += ch

    def _input_history(self, ch: str) -> None:
        all_logs = self.app.get_recent_history(limit=50)
        logs = [e for e in all_logs if self.tag_filter in e.get("tags", [])] if self.tag_filter else all_logs

        if ch == "UP":
            self.selected_idx = max(0, self.selected_idx - 1)
        elif ch == "DOWN":
            self.selected_idx = min(len(logs) - 1, self.selected_idx + 1) if logs else 0
        elif ch == "x":
            self.app.export_csv()
        elif ch in ("DEL", "d"):
            if logs and 0 <= self.selected_idx < len(logs):
                entry = logs[self.selected_idx]
                self.app.delete_log(entry["start_id"])
                self.app.delete_log(entry["stop_id"])
                refreshed = self.app.get_recent_history(limit=50)
                if self.selected_idx >= len(refreshed):
                    self.selected_idx = max(0, self.selected_idx - 1)
        elif ch == "e":
            if logs and 0 <= self.selected_idx < len(logs):
                self.edit_entry = dict(logs[self.selected_idx])
                self.edit_new_task = ""
                self.edit_new_start = ""
                self.edit_new_end = ""
                self.edit_error = ""
                tags_str = " ".join(f"#{t}" for t in self.edit_entry.get("tags", []))
                self.input_text = self.edit_entry["task"] + (f" {tags_str}" if tags_str else "")
                self.mode = "EDIT_TASK"
        elif ch == "a":
            self.add_new_task = ""
            self.add_new_start = ""
            self.add_new_end = ""
            self.add_error = ""
            self.input_text = ""
            self.mode = "ADD_TASK"
        elif ch == "g":
            if self.tag_filter:
                self.tag_filter = None
                self.selected_idx = 0
            else:
                self.mode = "TAG_FILTER"
                self.selected_idx = 0

    def _input_tag_filter(self, ch: str) -> None:
        all_tags = self.app.get_all_tags()
        if ch == "\x1b":
            self.mode = "HISTORY"
            self.selected_idx = 0
        elif ch == "UP":
            self.selected_idx = max(0, self.selected_idx - 1)
        elif ch == "DOWN":
            self.selected_idx = min(len(all_tags) - 1, self.selected_idx + 1) if all_tags else 0
        elif ch in ("\r", "\n"):
            if all_tags and 0 <= self.selected_idx < len(all_tags):
                self.tag_filter = all_tags[self.selected_idx]
            self.mode = "HISTORY"
            self.selected_idx = 0

    def _input_edit_task(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "HISTORY"
        elif ch in ("\r", "\n"):
            self.edit_new_task = self.input_text.strip() if self.input_text.strip() else self.edit_entry["task"]
            if len(self.edit_new_task) < 1:
                self.edit_error = "Task name cannot be empty"
            else:
                self.edit_error = ""
                self.input_text = self.edit_entry["start_time"]
                self.mode = "EDIT_START"
        elif ch in ("\x08", "\x7f"):
            self.input_text = self.input_text[:-1]
        elif len(ch) == 1 and ch.isprintable():
            self.input_text += ch

    def _input_edit_start(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "HISTORY"
        elif ch in ("\r", "\n"):
            raw = self.input_text.strip()
            if not raw:
                self.edit_new_start = self.edit_entry["start_time"]
                self.edit_error = ""
                self.input_text = self.edit_entry["stop_time"]
                self.mode = "EDIT_END"
            else:
                parsed, err = parse_time_input(raw)
                if err:
                    self.edit_error = err
                elif datetime.strptime(parsed, TIME_FORMAT) > datetime.now():  # type: ignore[arg-type]
                    self.edit_error = "Start cannot be in the future"
                else:
                    self.edit_new_start = parsed  # type: ignore[assignment]
                    self.edit_error = ""
                    self.input_text = self.edit_entry["stop_time"]
                    self.mode = "EDIT_END"
        elif ch in ("\x08", "\x7f"):
            self.input_text = self.input_text[:-1]
        elif len(ch) == 1 and ch.isprintable():
            self.input_text += ch

    def _input_edit_end(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "HISTORY"
        elif ch in ("\r", "\n"):
            raw = self.input_text.strip()
            if not raw:
                new_end = self.edit_entry["stop_time"]
            else:
                parsed, err = parse_time_input(raw)
                if err:
                    self.edit_error = err
                    return
                new_end = parsed
            ok, err = self.app.edit_log(
                self.edit_entry["start_id"],
                self.edit_entry["stop_id"],
                new_task=self.edit_new_task,
                new_start=self.edit_new_start,
                new_end=new_end,
            )
            if ok:
                self.edit_error = ""
                self.mode = "HISTORY"
            else:
                self.edit_error = err
        elif ch in ("\x08", "\x7f"):
            self.input_text = self.input_text[:-1]
        elif len(ch) == 1 and ch.isprintable():
            self.input_text += ch

    def _input_add_task(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "HISTORY"
        elif ch in ("\r", "\n"):
            task = self.input_text.strip()
            if not task:
                self.add_error = "Task name cannot be empty"
            else:
                self.add_new_task = task
                self.add_error = ""
                default_start = (datetime.now() - timedelta(hours=1)).strftime(TIME_FORMAT)
                self.input_text = default_start
                self.mode = "ADD_START"
        elif ch in ("\x08", "\x7f"):
            self.input_text = self.input_text[:-1]
        elif len(ch) == 1 and ch.isprintable():
            self.input_text += ch

    def _input_add_start(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "HISTORY"
        elif ch in ("\r", "\n"):
            raw = self.input_text.strip()
            if not raw:
                self.add_new_start = (datetime.now() - timedelta(hours=1)).strftime(TIME_FORMAT)
            else:
                parsed, err = parse_time_input(raw)
                if err:
                    self.add_error = err
                    return
                if datetime.strptime(parsed, TIME_FORMAT) > datetime.now():  # type: ignore[arg-type]
                    self.add_error = "Start cannot be in the future"
                    return
                self.add_new_start = parsed  # type: ignore[assignment]
            self.add_error = ""
            self.input_text = datetime.now().strftime(TIME_FORMAT)
            self.mode = "ADD_END"
        elif ch in ("\x08", "\x7f"):
            self.input_text = self.input_text[:-1]
        elif len(ch) == 1 and ch.isprintable():
            self.input_text += ch

    def _input_add_end(self, ch: str) -> None:
        if ch == "\x1b":
            self.mode = "HISTORY"
        elif ch in ("\r", "\n"):
            raw = self.input_text.strip()
            if not raw:
                end_str = datetime.now().strftime(TIME_FORMAT)
            else:
                parsed, err = parse_time_input(raw)
                if err:
                    self.add_error = err
                    return
                end_str = parsed  # type: ignore[assignment]
            s = datetime.strptime(self.add_new_start, TIME_FORMAT)
            e = datetime.strptime(end_str, TIME_FORMAT)
            if s >= e:
                self.add_error = "Start must be before End"
            elif (e - s).total_seconds() > 86400:
                self.add_error = "Session cannot exceed 24 hours"
            else:
                ok = self.app.add_manual_log(self.add_new_task, self.add_new_start, end_str)
                if ok:
                    self.add_error = ""
                    self.mode = "HISTORY"
                else:
                    self.add_error = "Failed to add entry"
        elif ch in ("\x08", "\x7f"):
            self.input_text = self.input_text[:-1]
        elif len(ch) == 1 and ch.isprintable():
            self.input_text += ch

    def _input_help(self, ch: str) -> None:
        # Any key returns to dashboard (q is already handled globally)
        if ch == "\x1b":
            self.mode = "DASH"
