# TimeTrace ⏱️

**A zero-dependency TUI time tracker built entirely with the Python standard library.**

Track tasks, view reports, manage history — all from your terminal.

---

## Features

- 🖥️ **Interactive TUI** — Dashboard with live timer, heatmap, and session history
- 🏷️ **Tag support** — Add `#tags` inline when creating tasks for categorisation
- 📊 **Reports** — Per-project and per-tag time breakdowns (today / week / month / all)
- 🔥 **Activity heatmap** — GitHub-style grid showing work patterns
- 📜 **History manager** — Browse, edit, delete, and add log entries
- 🕰️ **Retroactive start** — Forgot to start? Backdate it
- 🔔 **Native notifications** — Toast alerts on Windows, macOS, and Linux
- 🌐 **Webhook hooks** — Trigger HTTP webhooks on task start/stop
- 💾 **Auto-backup** — Database backed up on every task start
- 🎨 **Themes** — Default, Dark, and Retro colour schemes
- ⚙️ **Configurable** — Idle threshold, heatmap range, notification toggle
- 📤 **CSV export** — Full log export for external analysis
- 🚫 **Zero dependencies** — Pure Python standard library

---

## Installation

### Quick Start

```bash
# Clone the repo
git clone https://github.com/your-username/TimeTrace.git
cd TimeTrace

# Run directly
python trace.py
```

### Shell Alias (recommended)

Run the installer to add a `tt` command to your shell:

```bash
python install.py
```

After restarting your terminal:

```bash
tt          # Launch TUI
```

### As a Python Module

```bash
python -m timetrace
```

---

## Usage

Launch the TUI with `python trace.py` (or `tt` if you installed the alias).

### TUI Keybindings

#### Dashboard

| Key | Action                       |
|-----|------------------------------|
| `s` | Select a recent project      |
| `n` | Start a new task (type name) |
| `t` | Stop the active task         |
| `r` | Open reports view            |
| `f` | Retroactive start ("I forgot") |
| `h` | Open history manager         |
| `c` | Open configuration           |
| `b` | Manual database backup       |
| `?` | Help / keybinding reference  |
| `q` | Quit                         |

#### History Manager

| Key      | Action                    |
|----------|---------------------------|
| `↑` / `↓` | Navigate entries        |
| `a`      | Add a new manual entry    |
| `e`      | Edit the selected entry   |
| `d` / `DEL` | Delete selected entry |
| `x`      | Export all logs to CSV     |
| `g`      | Toggle tag filter          |
| `q`      | Back to dashboard         |

#### Reports

| Key   | Action                          |
|-------|---------------------------------|
| `1`   | Filter: Today                   |
| `2`   | Filter: This week               |
| `3`   | Filter: This month              |
| `4`   | Filter: All time                |
| `5`   | Toggle between Project / Tag view |
| `q`   | Back to dashboard               |

#### Configuration

| Key      | Action           |
|----------|------------------|
| `↑` / `↓` | Navigate options |
| `Enter`  | Toggle / cycle value |
| `q`      | Back to dashboard |

### Tags

Add tags by including `#tag` anywhere in the task name:

```
Code review #dev #meeting
```

Tags are automatically extracted, stored separately, and shown in history, reports, and the dashboard.

---

## Configuration

Configuration is stored in `hooks.json` in your app data directory.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `idle_threshold` | int | `300` | Seconds before idle warning appears |
| `auto_backup` | bool | `true` | Auto-backup on task start |
| `backup_freq` | string | `"STOP"` | Backup frequency: STOP / DAILY / WEEKLY |
| `theme` | string | `"Default"` | UI theme: Default / Dark / Retro |
| `heatmap_days` | int | `7` | Number of days shown in heatmap |
| `heatmap_start` | int | `6` | Heatmap start hour (0–23) |
| `heatmap_end` | int | `23` | Heatmap end hour (0–23) |
| `heatmap_weekdays` | string | `"MTWTFSS"` | Days to show (use `-` to hide) |
| `notifications` | bool | `true` | Native OS notifications |
| `feature_billing` | bool | `false` | Billing feature flag |
| `feature_html_report` | bool | `false` | HTML report feature flag |

### Data Location

| OS | Path |
|----|------|
| Windows | `%LOCALAPPDATA%\TimeTrace\` |
| macOS / Linux | `~/.timetrace/` |

---

## Architecture

```
timetrace/
├── __init__.py    # Package exports, VERSION
├── __main__.py    # python -m timetrace support
├── console.py     # Terminal rendering & keyboard input
├── platform.py    # OS-specific helpers (app dir, idle)
├── config.py      # ConfigManager, THEMES, constants
├── hooks.py       # Webhook HookManager & Notifier
├── database.py    # TimeTrace core — all SQLite operations
├── tui.py         # TraceTUI — drawing & input handling
└── utils.py       # parse_tags(), parse_time_input()
```

### Data Flow

```
User Input → TraceTUI._input() → TimeTrace (DB operations)
                                      ↓
              TraceTUI._draw() ← Cache (active, projects, history)
```

### Database Schema

```sql
logs (id INTEGER PK, timestamp TEXT, action TEXT, task TEXT)
tags (id INTEGER PK, name TEXT UNIQUE)
log_tags (log_id FK → logs, tag_id FK → tags)
```

---

## Requirements

- **Python 3.8+**
- No external dependencies

---

## License

MIT
