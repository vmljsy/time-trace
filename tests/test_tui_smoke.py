
from unittest.mock import MagicMock, patch
import pytest
from timetrace.tui import TraceTUI

@pytest.fixture
def mock_app():
    app = MagicMock()
    app.get_config.return_value = {
        "heatmap_start": 6,
        "heatmap_end": 23,
        "heatmap_weekdays": "MTWTFSS",
        "spinner_style": "dots",
    }
    app.get_heatmap_matrix.return_value = []
    app.get_today_total.return_value = "0h 0m"
    return app

@patch("timetrace.tui.Console")
def test_tui_draw_timeline_smoke(mock_console_cls, mock_app):
    """Smoke test to ensure _draw_timeline runs without error."""
    mock_console = mock_console_cls.return_value
    tui = TraceTUI(mock_app)
    
    # Mock timeline data: [("Monday", [("ProjectA", 9.0, 10.0)])]
    tui.cached_timeline = [("Mon", [("ProjectA", 9.0, 10.0)])]
    
    # Mock theme
    theme = {
        "title": "TimeTrace",
        "dim": "",
        "heatmap_none": "",
        "text": "\033[0m",
    }
    
    # Run the method
    try:
        tui._draw_timeline(20, 80, theme)
    except Exception as e:
        pytest.fail(f"_draw_timeline raised an exception: {e}")

@patch("timetrace.tui.Console")
def test_tui_init_spinner(mock_console_cls, mock_app):
    """Ensure spinner is initialized correctly."""
    tui = TraceTUI(mock_app)
    assert tui.spinner is not None
    assert tui.current_spinner_frame == ""
