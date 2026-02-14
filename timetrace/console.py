"""
Console — Low-level terminal rendering and keyboard input.

Provides a buffered-draw model: write to an internal grid, then flush
the entire frame at once to avoid flicker.  Handles wide characters
(emoji, CJK) gracefully and abstracts platform key-reading differences.
"""

from __future__ import annotations

import os
import shutil
import sys
import unicodedata

if os.name == "nt":
    import msvcrt
else:
    import termios
    import tty


class Console:
    """Buffered terminal renderer with keyboard input support."""

    def __init__(self) -> None:
        self.width: int = 80
        self.height: int = 24
        self.buffer: list[list[str]] = []
        if sys.version_info >= (3, 7):
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        self._get_size()
        if os.name == "nt":
            os.system("")  # Enable VT100 escape sequences on Windows
        self.clear_buffer()

    # ------------------------------------------------------------------
    # Size detection
    # ------------------------------------------------------------------
    def _get_size(self) -> None:
        """Refresh cached terminal dimensions."""
        try:
            cols, lines = shutil.get_terminal_size()
        except ValueError:
            cols, lines = 80, 24

        if cols != self.width or lines != self.height:
            self.width = cols
            self.height = lines
            self.clear_buffer()

    # ------------------------------------------------------------------
    # Buffer management
    # ------------------------------------------------------------------
    def clear_buffer(self) -> None:
        """Reset the internal character grid to spaces."""
        self.buffer = [[" " for _ in range(self.width)] for _ in range(self.height)]

    def print_at(self, y: int, x: int, text: str, style: str = "") -> None:
        """Write *text* into the buffer at row *y*, column *x*.

        Wide characters (emoji, CJK) correctly consume two cells.
        If *text* contains newlines, each line is printed at successive rows.
        """
        # Handle multi-line strings
        lines = text.split('\n')
        for line_offset, line in enumerate(lines):
            current_y = y + line_offset
            if not (0 <= current_y < self.height):
                continue
            if x >= self.width:
                continue

            col = 0  # visual column offset
            for char in line:
                pos = x + col
                if pos >= self.width:
                    break

                eaw = unicodedata.east_asian_width(char)
                char_width = 2 if eaw in ("W", "F") else 1

                # Skip writing space characters to allow text layering
                if char != ' ':
                    self.buffer[current_y][pos] = f"{style}{char}\033[0m"

                    # Wide chars occupy 2 cells — blank the next cell
                    if char_width == 2 and pos + 1 < self.width:
                        self.buffer[current_y][pos + 1] = ""

                col += char_width

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def draw(self) -> None:
        """Flush the buffer to stdout as a single frame write."""
        sys.stdout.write("\033[H")  # cursor to top-left

        output: list[str] = []
        for y, row in enumerate(self.buffer):
            line = "".join(row)
            if y == self.height - 1:
                # Trim last char on the final line to prevent scroll
                output.append(line[:-1])
            else:
                output.append(line)

        sys.stdout.write("\n".join(output))
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------
    def get_key(self) -> str:
        """Block until a key is pressed and return a normalised string.

        Special keys are returned as ``'UP'``, ``'DOWN'``, ``'LEFT'``,
        ``'RIGHT'``, ``'DEL'``.  Printable keys are returned as-is.
        """
        if os.name == "nt":
            ch = msvcrt.getch()
            if ch in (b"\x00", b"\xe0"):  # special-key prefix
                ch = msvcrt.getch()
                _MAP = {b"H": "UP", b"P": "DOWN", b"S": "DEL", b"M": "RIGHT", b"K": "LEFT"}
                return _MAP.get(ch, "")
            return ch.decode("utf-8", "ignore")

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                _MAP = {"[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT"}
                return _MAP.get(seq, "")
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
