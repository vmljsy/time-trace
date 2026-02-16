"""
Config — Application configuration, theme definitions, and constants.
"""

from __future__ import annotations

import json
import os
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# Distinct ANSI 256 colors for per-project timeline blocks.
# Projects are assigned a colour via ``hash(name) % len(PROJECT_COLORS)``.
PROJECT_COLORS: list[str] = [
    "\033[38;5;204m",  # rose
    "\033[38;5;39m",   # blue
    "\033[38;5;214m",  # orange
    "\033[38;5;48m",   # green
    "\033[38;5;141m",  # purple
    "\033[38;5;226m",  # yellow
    "\033[38;5;51m",   # cyan
    "\033[38;5;208m",  # amber
    "\033[38;5;183m",  # lavender
    "\033[38;5;114m",  # lime
]

THEMES: dict[str, dict[str, str]] = {
    "Default": {
        "box": "\033[0m",
        "header": "\033[1;36m",
        "highlight": "\033[1;32m",
        "warn": "\033[5;33m",
        "bar": "\033[36m",
        "text": "\033[0m",
        "dim": "\033[2m",
        "success": "\033[32m",
        "error": "\033[91m",
        "tag": "\033[36m",
        "active": "\033[1;32m",
        "title" : "",
        "heatmap_none": "\033[2m",
        "heatmap_low": "\033[32m",
        "heatmap_medium": "\033[32m",
        "heatmap_high": "\033[1;32m",
        "heatmap_peak": "\033[1;32m",
        "hint_key": "\033[1;36m",
        "hint_text": "\033[0m",
    },
    "Dark": {
        "box": "\033[90m",
        "header": "\033[94m",
        "highlight": "\033[92m",
        "warn": "\033[91m",
        "bar": "\033[94m",
        "text": "\033[37m",
        "dim": "\033[2;37m",
        "success": "\033[92m",
        "error": "\033[91m",
        "tag": "\033[96m",
        "active": "\033[1;92m",
        "title" : "",
        "heatmap_none": "\033[2m",
        "heatmap_low": "\033[34m",
        "heatmap_medium": "\033[34m",
        "heatmap_high": "\033[1;34m",
        "heatmap_peak": "\033[1;34m",
        "hint_key": "\033[1;94m",
        "hint_text": "\033[37m",
    },
    "Retro": {
        "box": "\033[32m",
        "header": "\033[32m",
        "highlight": "\033[1;32m",
        "warn": "\033[32m",
        "bar": "\033[32m",
        "text": "\033[32m",
        "dim": "\033[2;32m",
        "success": "\033[1;32m",
        "error": "\033[32m",
        "tag": "\033[32m",
        "active": "\033[1;5;32m",
        "title" : "",
        "heatmap_none": "\033[2;32m",
        "heatmap_low": "\033[32m",
        "heatmap_medium": "\033[32m",
        "heatmap_high": "\033[1;32m",
        "heatmap_peak": "\033[1;5;32m",
        "hint_key": "\033[1;5;32m",
        "hint_text": "\033[32m",
    },
    "Ocean": {
        "box": "\033[36m",
        "header": "\033[1;96m",
        "highlight": "\033[1;94m",
        "warn": "\033[1;93m",
        "bar": "\033[38;5;39m",
        "text": "\033[96m",
        "dim": "\033[2;36m",
        "success": "\033[38;5;45m",
        "error": "\033[38;5;203m",
        "tag": "\033[38;5;51m",
        "active": "\033[1;38;5;87m",
        "title" : """████████╗██╗███╗   ███╗███████╗████████╗██████╗  █████╗  ██████╗███████╗
╚══██╔══╝██║████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██╔════╝
   ██║   ██║██╔████╔██║█████╗     ██║   ██████╔╝███████║██║     █████╗  
   ██║   ██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██╗██╔══██║██║     ██╔══╝  
   ██║   ██║██║ ╚═╝ ██║███████╗   ██║   ██║  ██║██║  ██║╚██████╗███████╗
   ╚═╝   ╚═╝╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝""",
        "heatmap_none": "\033[2;36m",
        "heatmap_low": "\033[36m",
        "heatmap_medium": "\033[38;5;39m",
        "heatmap_high": "\033[1;38;5;45m",
        "heatmap_peak": "\033[1;38;5;51m",
        "hint_key": "\033[1;96m",
        "hint_text": "\033[96m",
    },
    "Sunset": {
        "box": "\033[38;5;208m",
        "header": "\033[1;38;5;214m",
        "highlight": "\033[1;38;5;203m",
        "warn": "\033[1;38;5;196m",
        "bar": "\033[38;5;209m",
        "text": "\033[38;5;223m",
        "dim": "\033[2;38;5;180m",
        "success": "\033[38;5;228m",
        "error": "\033[38;5;196m",
        "tag": "\033[38;5;217m",
        "active": "\033[1;38;5;220m",
        "title" : """                                 ___           ___                         ___           ___           ___           ___     
      ___            ___        /  /\         /  /\          ___          /  /\         /  /\         /  /\         /  /\    
     /__/\          /__/\      /  /::|       /  /::\        /__/\        /  /::\       /  /::\       /  /::\       /  /::\   
     \  \:\         \__\:\    /  /:|:|      /  /:/\:\       \  \:\      /  /:/\:\     /  /:/\:\     /  /:/\:\     /  /:/\:\  
      \__\:\        /  /::\  /  /:/|:|__   /  /::\ \:\       \__\:\    /  /::\ \:\   /  /::\ \:\   /  /:/  \:\   /  /::\ \:\ 
      /  /::\    __/  /:/\/ /__/:/_|::::\ /__/:/\:\ \:\      /  /::\  /__/:/\:\_\:\ /__/:/\:\_\:\ /__/:/ \  \:\ /__/:/\:\ \:\
     /  /:/\:\  /__/\/:/~~  \__\/  /~~/:/ \  \:\ \:\_\/     /  /:/\:\ \__\/~|::\/:/ \__\/  \:\/:/ \  \:\  \__\/ \  \:\ \:\_\/
    /  /:/__\/  \  \::/           /  /:/   \  \:\ \:\      /  /:/__\/    |  |:|::/       \__\::/   \  \:\        \  \:\ \:\  
   /__/:/        \  \:\          /  /:/     \  \:\_\/     /__/:/         |  |:|\/        /  /:/     \  \:\        \  \:\_\/  
   \__\/          \__\/         /__/:/       \  \:\       \__\/          |__|:|~        /__/:/       \  \:\        \  \:\    
                                \__\/         \__\/                       \__\|         \__\/         \__\/         \__\/    """,
        "heatmap_none": "\033[2;38;5;180m",
        "heatmap_low": "\033[38;5;208m",
        "heatmap_medium": "\033[38;5;214m",
        "heatmap_high": "\033[1;38;5;220m",
        "heatmap_peak": "\033[1;38;5;228m",
        "hint_key": "\033[1;38;5;214m",
        "hint_text": "\033[38;5;223m",
    },
    "Forest": {
        "box": "\033[38;5;22m",
        "header": "\033[1;38;5;28m",
        "highlight": "\033[1;38;5;34m",
        "warn": "\033[1;38;5;184m",
        "bar": "\033[38;5;28m",
        "text": "\033[38;5;34m",
        "dim": "\033[2;38;5;28m",
        "success": "\033[38;5;40m",
        "error": "\033[38;5;160m",
        "tag": "\033[38;5;70m",
        "active": "\033[1;38;5;46m",
        "title" : """ ____  ____  __  __  ____  ____  ____    __    ___  ____ 
(_  _)(_  _)(  \/  )( ___)(_  _)(  _ \  /__\  / __)( ___)
  )(   _)(_  )    (  )__)   )(   )   / /(__)\( (__  )__) 
 (__) (____)(_/\/\_)(____) (__) (_)\_)(__)(__)\___)(____)""",
        "heatmap_none": "\033[2;38;5;22m",
        "heatmap_low": "\033[38;5;28m",
        "heatmap_medium": "\033[38;5;34m",
        "heatmap_high": "\033[1;38;5;40m",
        "heatmap_peak": "\033[1;38;5;46m",
        "hint_key": "\033[1;38;5;34m",
        "hint_text": "\033[38;5;34m",
    },
    "Nord": {
        "box": "\033[38;5;67m",
        "header": "\033[1;38;5;111m",
        "highlight": "\033[1;38;5;150m",
        "warn": "\033[1;38;5;215m",
        "bar": "\033[38;5;109m",
        "text": "\033[38;5;254m",
        "dim": "\033[2;38;5;245m",
        "success": "\033[38;5;150m",
        "error": "\033[38;5;203m",
        "tag": "\033[38;5;139m",
        "active": "\033[1;38;5;187m",
        "title" : """████████ ██ ███    ███ ███████ ████████ ██████   █████   ██████ ███████ 
   ██    ██ ████  ████ ██         ██    ██   ██ ██   ██ ██      ██      
   ██    ██ ██ ████ ██ █████      ██    ██████  ███████ ██      █████   
   ██    ██ ██  ██  ██ ██         ██    ██   ██ ██   ██ ██      ██      
   ██    ██ ██      ██ ███████    ██    ██   ██ ██   ██  ██████ ███████ """,
        "heatmap_none": "\033[2;38;5;245m",
        "heatmap_low": "\033[38;5;67m",
        "heatmap_medium": "\033[38;5;109m",
        "heatmap_high": "\033[1;38;5;150m",
        "heatmap_peak": "\033[1;38;5;187m",
        "hint_key": "\033[1;38;5;111m",
        "hint_text": "\033[38;5;254m",
    },
    "Dracula": {
        "box": "\033[38;5;61m",
        "header": "\033[1;38;5;141m",
        "highlight": "\033[1;38;5;212m",
        "warn": "\033[1;38;5;228m",
        "bar": "\033[38;5;141m",
        "text": "\033[38;5;253m",
        "dim": "\033[2;38;5;240m",
        "success": "\033[38;5;84m",
        "error": "\033[38;5;203m",
        "tag": "\033[38;5;117m",
        "active": "\033[1;38;5;212m",
        "title" : "",
        "heatmap_none": "\033[2;38;5;240m",
        "heatmap_low": "\033[38;5;61m",
        "heatmap_medium": "\033[38;5;141m",
        "heatmap_high": "\033[1;38;5;141m",
        "heatmap_peak": "\033[1;38;5;212m",
        "hint_key": "\033[1;38;5;141m",
        "hint_text": "\033[38;5;253m",
    },
    "Gruvbox": {
        "box": "\033[38;5;241m",
        "header": "\033[1;38;5;214m",
        "highlight": "\033[1;38;5;142m",
        "warn": "\033[1;38;5;208m",
        "bar": "\033[38;5;108m",
        "text": "\033[38;5;223m",
        "dim": "\033[2;38;5;246m",
        "success": "\033[38;5;142m",
        "error": "\033[38;5;167m",
        "tag": "\033[38;5;109m",
        "active": "\033[1;38;5;214m",
        "title" : "",
        "heatmap_none": "\033[2;38;5;246m",
        "heatmap_low": "\033[38;5;108m",
        "heatmap_medium": "\033[38;5;142m",
        "heatmap_high": "\033[1;38;5;142m",
        "heatmap_peak": "\033[1;38;5;214m",
        "hint_key": "\033[1;38;5;214m",
        "hint_text": "\033[38;5;223m",
    },
    "Monokai": {
        "box": "\033[38;5;59m",
        "header": "\033[1;38;5;81m",
        "highlight": "\033[1;38;5;185m",
        "warn": "\033[1;38;5;208m",
        "bar": "\033[38;5;141m",
        "text": "\033[38;5;252m",
        "dim": "\033[2;38;5;243m",
        "success": "\033[38;5;118m",
        "error": "\033[38;5;197m",
        "tag": "\033[38;5;141m",
        "active": "\033[1;38;5;226m",
        "title" : "",
        "heatmap_none": "\033[2;38;5;243m",
        "heatmap_low": "\033[38;5;59m",
        "heatmap_medium": "\033[38;5;141m",
        "heatmap_high": "\033[1;38;5;185m",
        "heatmap_peak": "\033[1;38;5;226m",
        "hint_key": "\033[1;38;5;81m",
        "hint_text": "\033[38;5;252m",
    },
    "Solarized": {
        "box": "\033[38;5;240m",
        "header": "\033[1;38;5;33m",
        "highlight": "\033[1;38;5;64m",
        "warn": "\033[1;38;5;136m",
        "bar": "\033[38;5;37m",
        "text": "\033[38;5;244m",
        "dim": "\033[2;38;5;240m",
        "success": "\033[38;5;64m",
        "error": "\033[38;5;160m",
        "tag": "\033[38;5;125m",
        "active": "\033[1;38;5;37m",
        "title" : "",
        "heatmap_none": "\033[2;38;5;240m",
        "heatmap_low": "\033[38;5;240m",
        "heatmap_medium": "\033[38;5;37m",
        "heatmap_high": "\033[1;38;5;64m",
        "heatmap_peak": "\033[1;38;5;33m",
        "hint_key": "\033[1;38;5;33m",
        "hint_text": "\033[38;5;244m",
    },
    "Synthwave": {
        "box": "\033[38;5;90m",
        "header": "\033[1;38;5;201m",
        "highlight": "\033[1;38;5;51m",
        "warn": "\033[1;38;5;226m",
        "bar": "\033[38;5;165m",
        "text": "\033[38;5;219m",
        "dim": "\033[2;38;5;183m",
        "success": "\033[38;5;87m",
        "error": "\033[38;5;196m",
        "tag": "\033[38;5;213m",
        "active": "\033[1;38;5;201m",
        "title" : "",
        "heatmap_none": "\033[2;38;5;183m",
        "heatmap_low": "\033[38;5;90m",
        "heatmap_medium": "\033[38;5;165m",
        "heatmap_high": "\033[1;38;5;201m",
        "heatmap_peak": "\033[1;38;5;51m",
        "hint_key": "\033[1;38;5;201m",
        "hint_text": "\033[38;5;219m",
    },
    "Cyberpunk": {
        "box": "\033[38;5;21m",
        "header": "\033[1;38;5;51m",
        "highlight": "\033[1;38;5;201m",
        "warn": "\033[1;38;5;226m",
        "bar": "\033[38;5;45m",
        "text": "\033[38;5;51m",
        "dim": "\033[2;38;5;31m",
        "success": "\033[38;5;46m",
        "error": "\033[38;5;196m",
        "tag": "\033[38;5;199m",
        "active": "\033[1;5;38;5;51m",
        "title" : "",
        "heatmap_none": "\033[2;38;5;31m",
        "heatmap_low": "\033[38;5;21m",
        "heatmap_medium": "\033[38;5;45m",
        "heatmap_high": "\033[1;38;5;51m",
        "heatmap_peak": "\033[1;38;5;201m",
        "hint_key": "\033[1;38;5;51m",
        "hint_text": "\033[38;5;51m",
    },
    "Rose Pine": {
        "box": "\033[38;5;95m",
        "header": "\033[1;38;5;182m",
        "highlight": "\033[1;38;5;217m",
        "warn": "\033[1;38;5;173m",
        "bar": "\033[38;5;139m",
        "text": "\033[38;5;188m",
        "dim": "\033[2;38;5;102m",
        "success": "\033[38;5;151m",
        "error": "\033[38;5;204m",
        "tag": "\033[38;5;175m",
        "active": "\033[1;38;5;217m",
        "title" : "",
        "heatmap_none": "\033[2;38;5;102m",
        "heatmap_low": "\033[38;5;95m",
        "heatmap_medium": "\033[38;5;139m",
        "heatmap_high": "\033[1;38;5;182m",
        "heatmap_peak": "\033[1;38;5;217m",
        "hint_key": "\033[1;38;5;182m",
        "hint_text": "\033[38;5;188m",
    },
    "Tokyo Night": {
        "box": "\033[38;5;237m",
        "header": "\033[1;38;5;111m",
        "highlight": "\033[1;38;5;170m",
        "warn": "\033[1;38;5;215m",
        "bar": "\033[38;5;75m",
        "text": "\033[38;5;188m",
        "dim": "\033[2;38;5;243m",
        "success": "\033[38;5;115m",
        "error": "\033[38;5;203m",
        "tag": "\033[38;5;183m",
        "active": "\033[1;38;5;147m",
        "title" : "",
        "heatmap_none": "\033[2;38;5;243m",
        "heatmap_low": "\033[38;5;237m",
        "heatmap_medium": "\033[38;5;75m",
        "heatmap_high": "\033[1;38;5;111m",
        "heatmap_peak": "\033[1;38;5;170m",
        "hint_key": "\033[1;38;5;111m",
        "hint_text": "\033[38;5;188m",
    },
}

_CONFIG_DEFAULTS: dict[str, Any] = {
    "idle_threshold": 300,
    "auto_stop_idle": False,
    "auto_resume_idle": False,
    "idle_sound": False,
    "auto_backup": True,
    "backup_freq": "STOP",
    "feature_billing": False,
    "feature_html_report": False,
    "theme": "Default",
    "heatmap_days": 7,
    "heatmap_start": 6,
    "heatmap_end": 23,
    "heatmap_weekdays": "MTWTFSS",
    "notifications": True,
    "on_start": [],
    "on_stop": [],
    "spinner_style": "dots",
}


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------
class ConfigManager:
    """Read / write the JSON configuration file (``hooks.json``)."""

    def __init__(self, app_dir: str) -> None:
        self.path: str = os.path.join(app_dir, "hooks.json")
        # Ensure the file exists with at least an empty object
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump({"on_start": [], "on_stop": []}, fh, indent=4)

    def get(self) -> dict[str, Any]:
        """Return merged defaults + saved config."""
        cfg = dict(_CONFIG_DEFAULTS)
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    saved = json.load(fh)
                cfg.update(saved)
            except (json.JSONDecodeError, OSError):
                pass  # fall back to defaults
        return cfg

    def update(self, key: str, value: Any) -> None:
        """Persist a single config key."""
        cfg = self.get()
        cfg[key] = value
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=4)
