"""Allow running as ``python -m timetrace``."""

from timetrace.database import TimeTrace
from timetrace.tui import TraceTUI

if __name__ == "__main__":
    try:
        TraceTUI(TimeTrace()).run()
    except Exception as e:
        print(f"Error: {e}")
