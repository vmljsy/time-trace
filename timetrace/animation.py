"""
Animation — Extensible spinner and animation system.

Provides a Spinner protocol and concrete implementations for various
animation styles (dots, lines, bouncing), plus a registry for easy lookup.
"""

from __future__ import annotations

from typing import List, Protocol


class Spinner(Protocol):
    """Protocol defining the interface for all spinners."""
    
    def next_frame(self) -> str:
        """Advance the animation and return the next frame."""
        ...

    def reset(self) -> None:
        """Reset the animation to its initial state."""
        ...


class FrameSpinner:
    """Standard spinner that cycles through a list of frames."""

    def __init__(self, frames: List[str]):
        self.frames = frames
        self._idx = 0

    def next_frame(self) -> str:
        frame = self.frames[self._idx]
        self._idx = (self._idx + 1) % len(self.frames)
        return frame

    def reset(self) -> None:
        self._idx = 0


class BouncingSpinner:
    """Spinner that bounces back and forth through frames (ping-pong)."""

    def __init__(self, frames: List[str]):
        self.frames = frames
        self._idx = 0
        self._direction = 1  # 1 for forward, -1 for backward

    def next_frame(self) -> str:
        if not self.frames:
            return ""
            
        frame = self.frames[self._idx]
        
        # Calculate next index
        next_idx = self._idx + self._direction
        
        # Bounce logic
        if next_idx >= len(self.frames):
            self._direction = -1
            next_idx = len(self.frames) - 2 # Step back
        elif next_idx < 0:
            self._direction = 1
            next_idx = 1 # Step forward
            
        self._idx = max(0, min(next_idx, len(self.frames) - 1))
        return frame

    def reset(self) -> None:
        self._idx = 0
        self._direction = 1


# ------------------------------------------------------------------
# Animation Frames
# ------------------------------------------------------------------

DOTS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
LINE = ["-", "\\", "|", "/"]
ARROW = ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"]
PULSE = ["•", "○", "•", "·"]
BOUNCE_BALL = [
    "( ●    )", "(  ●   )", "(   ●  )", "(    ● )", 
    "(     ●)", "(    ● )", "(   ●  )", "(  ●   )"
]
RUNNER = ["( o_)", "( o_)", "( _o)", "( _o)"]

# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

SPINNERS: dict[str, Spinner] = {
    "dots": FrameSpinner(DOTS),
    "line": FrameSpinner(LINE),
    "arrow": FrameSpinner(ARROW),
    "pulse": FrameSpinner(PULSE),
    "bouncing": FrameSpinner(BOUNCE_BALL), # Frames already simulate bounce loop
    "runner": FrameSpinner(RUNNER),
}

def get_spinner(name: str) -> Spinner:
    """Retrieve a spinner by name, defaulting to 'dots'."""
    return SPINNERS.get(name, SPINNERS["dots"])
