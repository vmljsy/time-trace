"""
Hooks — Webhook triggers and native OS notifications.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import urllib.request
from typing import Any


class HookManager:
    """Fire webhooks on task start/stop events."""

    def __init__(self, app_dir: str) -> None:
        self.hooks_path: str = os.path.join(app_dir, "hooks.json")
        if not os.path.exists(self.hooks_path):
            with open(self.hooks_path, "w", encoding="utf-8") as fh:
                json.dump({"on_start": [], "on_stop": []}, fh, indent=4)

    def trigger(self, event: str, task: str, duration: str = "") -> None:
        """Asynchronously fire hooks for *event* (``on_start`` / ``on_stop``)."""
        threading.Thread(
            target=self._run_hooks, args=(event, task, duration), daemon=True
        ).start()

    def _run_hooks(self, event: str, task: str, duration: str) -> None:
        try:
            with open(self.hooks_path, "r", encoding="utf-8") as fh:
                hooks: list[dict[str, Any]] = json.load(fh).get(event, [])
            for hook in hooks:
                if hook.get("type") == "webhook":
                    payload = json.dumps({"text": f"{event}: {task} {duration}"}).encode()
                    req = urllib.request.Request(
                        hook["url"],
                        data=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # hooks must never crash the app


class Notifier:
    """Cross-platform native notification support.  Fails gracefully."""

    @staticmethod
    def send(title: str, message: str) -> None:
        """Send a native OS notification in a background thread."""
        try:
            threading.Thread(
                target=Notifier._send, args=(title, message), daemon=True
            ).start()
        except Exception:
            pass

    @staticmethod
    def _send(title: str, message: str) -> None:
        try:
            if os.name == "nt":
                ps_script = (
                    "[Windows.UI.Notifications.ToastNotificationManager, "
                    "Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
                    "[Windows.Data.Xml.Dom.XmlDocument, "
                    "Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null; "
                    f"$xml = '<toast><visual><binding template=\"ToastText02\">"
                    f'<text id=\"1\">{title}</text>'
                    f'<text id=\"2\">{message}</text>'
                    f"</binding></visual></toast>'; "
                    "$xd = New-Object Windows.Data.Xml.Dom.XmlDocument; "
                    "$xd.LoadXml($xml); "
                    "$toast = [Windows.UI.Notifications.ToastNotification]::new($xd); "
                    "[Windows.UI.Notifications.ToastNotificationManager]::"
                    "CreateToastNotifier('TimeTrace').Show($toast)"
                )
                subprocess.Popen(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            elif sys.platform == "darwin":
                subprocess.Popen(
                    [
                        "osascript", "-e",
                        f'display notification "{message}" with title "{title}"',
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    ["notify-send", title, message],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass  # notifications must never crash the app
