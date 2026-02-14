# Configuration Reference

TimeTrace stores configuration in `hooks.json` inside the app data directory.

## Data Directory

| OS | Path |
|----|------|
| Windows | `%LOCALAPPDATA%\TimeTrace\` |
| macOS / Linux | `~/.timetrace/` |

## Configuration Keys

### Behavior

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `idle_threshold` | `int` | `300` | Seconds of system inactivity before the idle warning appears on the dashboard |
| `auto_backup` | `bool` | `true` | Automatically create a database backup on every task start |
| `backup_freq` | `string` | `"STOP"` | Backup trigger frequency: `"STOP"` (every stop), `"DAILY"`, or `"WEEKLY"` |

### Visual

| Key | Type | Default | Options | Description |
|-----|------|---------|---------|-------------|
| `theme` | `string` | `"Default"` | `Default`, `Dark`, `Retro` | UI colour scheme |
| `heatmap_days` | `int` | `7` | `7`, `14`, `28` | Number of rows in the activity heatmap |
| `heatmap_start` | `int` | `6` | `0`–`10` | First hour shown in the heatmap |
| `heatmap_end` | `int` | `23` | `17`–`23` | Last hour shown in the heatmap |
| `heatmap_weekdays` | `string` | `"MTWTFSS"` | Any 7-char string | Days to display; use `-` to hide (e.g. `"MTWTF--"` for weekdays only) |

### Features

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `notifications` | `bool` | `true` | Send native OS notifications on task start/stop |
| `feature_billing` | `bool` | `false` | Enable billing features (reserved) |
| `feature_html_report` | `bool` | `false` | Enable HTML report generation (reserved) |

### Webhooks

Webhooks are configured via `on_start` and `on_stop` arrays in the same file:

```json
{
    "on_start": [
        {"type": "webhook", "url": "https://hooks.slack.com/..."}
    ],
    "on_stop": [
        {"type": "webhook", "url": "https://hooks.slack.com/..."}
    ]
}
```

Each hook fires asynchronously in a background thread and will silently fail on network errors.

## Backups

Database backups are saved to `<data_dir>/backups/backup_YYYYMMDD.db`.

- **Automatic**: Created on every task start (if `auto_backup` is enabled)
- **Manual**: Press `b` on the dashboard to trigger a backup
